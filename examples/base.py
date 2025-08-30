import asyncio
import sys
from pyframe import launch, command, Window
from pathlib import Path



@command
async def greet(window: Window, name: str) -> str:
    """
    Example greet command that also shows Python version.
    
    :param window: Active PyFrame window
    :param name: Person to greet
    :return: A greeting message incl. Python version
    """
    await asyncio.sleep(0.1)  # simulate async work

    pyver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    # Fenster-Titel setzen
    res = await window.set_title(
        title=f"Hello, {name}! (Python {pyver}) 👋"
    )

    if res:
        return f"Hello, {name}! You've been greeted from Python {pyver}! 👋"
    return f"Could not update title, but hello anyway {name}! 🙂 (Python {pyver})"






if __name__ == "__main__":
    try:
        asyncio.run(launch(path="basic.html",host="127.0.0.1",port=9000))
    except KeyboardInterrupt:
        print("Runtime beendet.")
