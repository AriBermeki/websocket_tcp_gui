import asyncio
import dataclasses
import json
import os
import struct
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union

from pydantic import BaseModel

T = TypeVar("T")


def make_json_safe(obj: Any) -> Any:
    """
    Convert arbitrary Python objects into JSON-serializable structures.

    Handles primitives, Pydantic models, dataclasses, paths,
    dictionaries, and iterables. Falls back to ``str(obj)``.

    :param obj: Any Python object.
    :return: A JSON-serializable representation.
    """
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    if dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)
    if isinstance(obj, dict):
        return {str(k): make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [make_json_safe(v) for v in obj]
    return str(obj)


def normalize_args(args: Optional[Any]) -> list:
    """
    Normalize arguments to a JSON-safe list.

    Ensures that function arguments are always passed as a list
    compatible with the JSON event loop.

    :param args: Optional argument or list of arguments.
    :return: JSON-safe list of arguments.
    """
    if args is None:
        return []
    if isinstance(args, list):
        return [make_json_safe(a) for a in args]
    return [make_json_safe(args)]


class ApiRequestModel(BaseModel):
    """Representation of a request sent to the Rust event loop."""
    id: int
    method: str
    args: List[Any]

    def to_json_array(self) -> list:
        """
        Convert the request into a JSON-safe array format.

        :return: List of ``[id, method, args]``.
        """
        return [self.id, self.method, [make_json_safe(a) for a in self.args]]


class ApiResponseModel(BaseModel):
    """Representation of a response returned from the Rust event loop."""
    id: int
    code: int
    msg: str
    result: Any

    @classmethod
    def from_array(cls, arr: List[Any]) -> "ApiResponseModel":
        """
        Construct a response model from an array.

        :param arr: List of 4 elements ``[id, code, msg, result]``.
        :return: Parsed response model.
        :raises ValueError: If the array format is invalid.
        """
        if not isinstance(arr, list) or len(arr) != 4:
            raise ValueError(f"Invalid ApiResponse array: {arr}")
        return cls(id=arr[0], code=arr[1], msg=arr[2], result=arr[3])


class ApiError(Exception):
    """Raised for errors reported by the Rust event loop."""

    def __init__(self, code: int, msg: str):
        super().__init__(f"[API-{code}] {msg}")
        self.code = code
        self.msg = msg


class PendingRegistry:
    """
    Manage pending futures and request IDs.

    Request IDs cycle from 0 to ``max_id`` with wrap-around.
    Ensures cleanup of futures to prevent memory leaks.
    """

    def __init__(self, max_id: int = 255):
        self._pending: Dict[int, asyncio.Future[Any]] = {}
        self._counter: int = 0
        self._max_id = max_id

    def next_id(self) -> int:
        """
        Generate the next free request ID.

        :return: Unique request ID.
        :raises RuntimeError: If no free ID is available.
        """
        for _ in range(self._max_id):
            self._counter = (self._counter + 1) % self._max_id
            if self._counter not in self._pending:
                return self._counter
        raise RuntimeError("No free request IDs available")

    def register(self, req_id: int, future: asyncio.Future[Any]) -> None:
        """Register a future under the given request ID."""
        self._pending[req_id] = future

    def pop(self, req_id: int, default: Optional[Any] = None) -> Optional[asyncio.Future[Any]]:
        """
        Remove and return a future.

        :param req_id: Request ID to remove.
        :param default: Default return value if not present.
        :return: The future or ``None``.
        """
        return self._pending.pop(req_id, default)

    def resolve(
        self,
        req_id: int,
        result: Any = None,
        error: Optional[Exception] = None
    ) -> None:
        """
        Resolve a pending future with a result or error.

        :param req_id: Request ID to resolve.
        :param result: Optional result value.
        :param error: Optional exception to set.
        """
        future = self._pending.pop(req_id, None)
        if future and not future.done():
            if error:
                future.set_exception(error)
            else:
                future.set_result(result)

    def cancel_all(self, exc: Optional[Exception] = None) -> None:
        """
        Cancel all pending futures.

        :param exc: Optional exception to set instead of cancellation.
        """
        for fut in self._pending.values():
            if not fut.done():
                if exc:
                    fut.set_exception(exc)
                else:
                    fut.cancel()
        self._pending.clear()


_pending = PendingRegistry()
task_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()


async def send_loop_event(data: list) -> Optional[list]:
    """
    Send a synchronous event to the Rust loop.

    A single request is sent and a single response is awaited.

    :param data: The request array.
    :return: The decoded response array.
    """
    port = int(os.environ.get("RUSTADDR", "9000"))
    reader, writer = await asyncio.open_connection("127.0.0.1", port)

    payload = json.dumps(data).encode("utf-8")
    writer.write(struct.pack(">I", len(payload)) + payload)
    await writer.drain()

    header = await reader.readexactly(4)
    (length,) = struct.unpack(">I", header)
    response_bytes = await reader.readexactly(length)

    writer.close()
    await writer.wait_closed()

    return json.loads(response_bytes.decode("utf-8"))


async def handle_event_loop_response(arr: list, future: Optional[asyncio.Future] = None):
    """
    Process a response from the Rust loop.

    If a future is provided, it is resolved directly.
    Otherwise, the response is matched against the registry.

    :param arr: Response array.
    :param future: Optional future to resolve.
    """
    resp = ApiResponseModel.from_array(arr)
    if future:
        if resp.code != 0:
            future.set_exception(ApiError(resp.code, resp.msg))
        else:
            future.set_result(resp.result)
    else:
        _pending.resolve(
            resp.id,
            error=ApiError(resp.code, resp.msg) if resp.code != 0 else None,
            result=None if resp.code != 0 else resp.result,
        )


async def gui_endless_event_loop_tasks():
    """
    Endless loop forwarding tasks to the Rust event loop.

    Continuously processes tasks from ``task_queue`` and dispatches
    them to the Rust backend. Pending futures are resolved with
    results or errors.
    """
    try:
        while True:
            task = await task_queue.get()
            future: asyncio.Future[Any] = task.pop("future", None)
            data = task.get("data")

            try:
                arr = await send_loop_event(data)
                if arr:
                    await handle_event_loop_response(arr, future=future)
            except Exception as e:
                if future and not future.done():
                    future.set_exception(e)
            finally:
                await asyncio.sleep(0.01)
    except asyncio.CancelledError:
        print("[INFO] gui_endless_event_loop_tasks() cancelled.")
    finally:
        print("[INFO] gui_endless_event_loop_tasks() terminated.")
        _pending.cancel_all(RuntimeError("Event loop terminated"))


async def eventloop_event_register_typed(
    method: str,
    args: Optional[Any] = None,
    result_type: Union[Type[BaseModel], Callable[[Any], T]] = dict,
) -> T:
    """
    Send a typed request to the event loop and await its response.

    * Arguments are normalized into a list.
    * All arguments are made JSON-safe.
    * The response is type-checked using Pydantic or a callable.

    :param method: The event method name.
    :param args: Optional arguments for the request.
    :param result_type: Expected result type. Can be a Pydantic model,
        a callable transformer, or a raw type.
    :return: The parsed response.
    :raises Exception: If the request fails or validation fails.
    """
    req_id = _pending.next_id()
    request = ApiRequestModel(id=req_id, method=method, args=normalize_args(args))
    future: asyncio.Future[T] = asyncio.get_event_loop().create_future()
    _pending.register(req_id, future)

    await task_queue.put({
        "data": request.to_json_array(),
        "future": future,
    })

    try:
        raw_result = await asyncio.wait_for(future, timeout=10.0)

        if isinstance(result_type, type) and issubclass(result_type, BaseModel):
            return result_type.model_validate(raw_result)
        if callable(result_type):
            return result_type(raw_result)
        return raw_result

    except Exception:
        _pending.pop(req_id)
        raise
    finally:
        _pending.pop(req_id, None)
