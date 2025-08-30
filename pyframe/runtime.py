import asyncio
from multiprocessing import get_context
from pathlib import Path
from typing import Optional, Union
from pygcc import create_webframe
from .connections import create_websocket_server
from .core import install_signal_handlers, shutdown_all_tasks, start_tracked_task
from .runtime_handle import gui_endless_event_loop_tasks
from .utils import find_free_ports_and_set_env, load_html


async def native_runtime(
    path: Optional[Union[Path, str]],
    host: str = "localhost",
    port: int = 8080
) -> None:
    """
    Launch the native runtime environment with WebSocket server,
    Rust event loop tasks, and a native webframe process.

    This function:
      * Finds and sets free ports in the environment.
      * Installs signal handlers for graceful shutdown.
      * Starts background tasks for the WebSocket server and GUI event loop.
      * Spawns a separate process for the webframe.
      * Waits for the close signal from the webframe and performs cleanup.

    :param html: HTML content or file path for the initial webframe view.
    :param host: Host address for the WebSocket server. Defaults to ``"localhost"``.
    :param port: Port for the WebSocket server. Defaults to ``8080``.
    :return: None
    """
    html = load_html(path)
    find_free_ports_and_set_env()
    install_signal_handlers()

    start_tracked_task(create_websocket_server(host, port))
    start_tracked_task(gui_endless_event_loop_tasks())
    loop = asyncio.get_running_loop()
    tasks = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task(loop)]
    ctx = get_context("spawn")
    with ctx.Manager() as manager:
        mp_event = manager.Event()
        p = ctx.Process(target=create_webframe, args=(html, host, port, mp_event,), daemon=False)
        p.start()

        # Wait for shutdown signal from webframe
        await loop.run_in_executor(None, mp_event.wait)
        [task.cancel() for task in tasks]

        def _join_or_kill():
            p.join(3.0)
            if p.is_alive():
                p.terminate()
                p.join()

        await loop.run_in_executor(None, _join_or_kill)

    await shutdown_all_tasks()
