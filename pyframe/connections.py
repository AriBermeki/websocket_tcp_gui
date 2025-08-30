import asyncio
import json
import os
import struct
from typing import Any, Dict, Optional

import websockets
from pydantic import BaseModel
from websockets import ServerConnection

from . import core
from .pyinvoke import make_callback


async def send_loop_event(data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Send an event payload to the Rust loop process via TCP.

    The payload is JSON-encoded and sent with a 4-byte big-endian
    length prefix. A JSON-decoded response is returned.

    :param data: Optional dictionary containing the payload.
    :return: A decoded response dictionary or ``None``.
    """
    port = int(os.environ["RUSTADDR"])
    reader, writer = await asyncio.open_connection("127.0.0.1", port)

    payload = json.dumps(data).encode()
    writer.write(struct.pack(">I", len(payload)) + payload)
    await writer.drain()

    header = await reader.readexactly(4)
    (length,) = struct.unpack(">I", header)

    response_bytes = await reader.readexactly(length)
    writer.close()
    await writer.wait_closed()
    return json.loads(response_bytes.decode())


async def handle_frontend_connections(websocket: ServerConnection) -> None:
    """
    Handle incoming WebSocket connections from frontend clients.

    Each received message is validated, dispatched to the appropriate
    callback handler via :func:`make_callback`, and the response is
    broadcast to all connected clients.

    :param websocket: The client WebSocket connection.
    """
    core.connected_clients.add(websocket)
    try:
        async for message in websocket:
            try:
                payload = json.loads(message.strip())
                if isinstance(payload, str):
                    payload = json.loads(payload)

                if not isinstance(payload, dict):
                    continue

                if all(k in payload for k in ("cmd", "result_id", "error_id", "payload")):
                    response = await make_callback(
                        payload["cmd"],
                        payload["result_id"],
                        payload["error_id"],
                        payload["payload"],
                    )

                    response_msg = (
                        response.model_dump_json(by_alias=True)
                        if isinstance(response, BaseModel)
                        else json.dumps(response)
                    )

                    await asyncio.gather(*(client.send(response_msg) for client in core.connected_clients))
                else:
                    print("[WARN] Incomplete message keys:", payload)
            except json.JSONDecodeError as e:
                print(f"[ERROR] Malformed JSON from {websocket.remote_address}: {e}")
            except Exception as e:
                print(f"[ERROR] Unexpected error handling message: {e}")
    except websockets.ConnectionClosed:
        print(f"[INFO] Client disconnected: {websocket.remote_address}")
    finally:
        core.connected_clients.discard(websocket)


async def create_websocket_server(host: str = "localhost", port: int = 8765) -> None:
    """
    Create and start a WebSocket server.

    The server accepts connections from frontend clients and routes
    messages to :func:`handle_frontend_connections`.

    :param host: The host address to bind the server. Defaults to ``"localhost"``.
    :param port: The port to bind the server. Defaults to ``8765``.
    """
    async with websockets.serve(handle_frontend_connections, host, port):
        await asyncio.Future()
