import asyncio
import signal
import sys
from typing import Any, Coroutine, Dict, Set

from websockets import ServerConnection


#: Global queue for tasks to be processed asynchronously.
task_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()

#: Futures waiting for responses, keyed by identifier.
_pending_responses: Dict[str, asyncio.Future[Any]] = {}

#: Background tasks started by the system.
background_tasks: Set[asyncio.Task] = set()

#: Currently connected WebSocket clients.
connected_clients: Set[ServerConnection] = set()

#: Timeout in seconds for awaiting responses.
RESPONSE_TIMEOUT = 5.0


def start_tracked_task(coro: Coroutine) -> asyncio.Task:
    """
    Start and track an asyncio task.

    The task is added to the global ``background_tasks`` set
    and automatically removed once completed.

    :param coro: The coroutine to execute as a task.
    :return: The created asyncio task.
    """
    task = asyncio.create_task(coro)
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)
    return task


async def shutdown_all_tasks():
    """
    Cancel and await all tracked background tasks.

    Ensures that all running tasks are stopped gracefully
    before shutdown completes.
    """
    for task in background_tasks:
        task.cancel()
    await asyncio.gather(*background_tasks, return_exceptions=True)


def install_signal_handlers():
    """
    Install signal handlers for graceful shutdown.

    On Unix systems, ``SIGINT`` and ``SIGTERM`` are bound to
    trigger :func:`shutdown_all_tasks`. On Windows, a warning
    is printed as signal handlers are not supported.

    .. note::
       On Windows, shutdown must be triggered manually.
    """
    if sys.platform != "win32":
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown_all_tasks()))
    else:
        print("[WARN] Signal handlers are not supported on Windows — shutdown must be manual.")
