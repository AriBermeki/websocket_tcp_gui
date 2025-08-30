import os
from pathlib import Path
import socket
from typing import Optional, Union

def load_html(path: Optional[Union[Path, str]]) -> str:
    """Load HTML content from current working directory or fallback message."""
    if path is None:
        return _fallback_html()

    HTML_SRC = Path.cwd() / path   # <--- statt __file__
    if not HTML_SRC.exists():
        return _fallback_html()

    return HTML_SRC.read_text(encoding="utf-8")

def _fallback_html() -> str:
    return r"""
<style>
@keyframes vibrate {
    0%   { transform: translate(-50%, -50%) rotate(0deg); }
    20%  { transform: translate(-49%, -50%) rotate(-1deg); }
    40%  { transform: translate(-51%, -50%) rotate(1deg); }
    60%  { transform: translate(-49%, -50%) rotate(-1deg); }
    80%  { transform: translate(-51%, -50%) rotate(1deg); }
    100% { transform: translate(-50%, -50%) rotate(0deg); }
}
</style>

<div style="
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    padding: 24px 32px;
    text-align: center;
    font-family: sans-serif;
    max-width: 400px;
    animation: vibrate 0.3s linear infinite;
">
    <h2 style="margin: 0; color: #333; font-size: 1.2rem;">
        ⚠️ HTML file not found - please check.
    </h2>
</div>
"""



def find_free_ports_and_set_env() -> None:
    """
    Find two free TCP ports and set them in the environment.

    The function discovers two available ports on localhost
    and assigns them to the environment variables:

      * ``RUSTADDR`` → port for the Rust backend
      * ``PYTHONADDR`` → port for the Python side

    Ports are guaranteed to be distinct.

    :return: None
    """
    def find_free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]

    port1 = find_free_port()
    port2 = find_free_port()
    while port1 == port2:
        port2 = find_free_port()

    os.environ['RUSTADDR'] = str(port1)
    os.environ['PYTHONADDR'] = str(port2)


def set_assets_env(
    name: Optional[str] = None,
    protocol: Optional[str] = None,
    entry: Optional[str] = None,
    debug_entry: Optional[str] = None,
):
    """
    Configure asset-related environment variables.

    Sets the following environment variables if provided:

      * ``NAME`` → application name
      * ``PROTOCOL`` → custom protocol (e.g., ``pyframe://``)
      * ``ENTRY`` → main entry point (HTML/JS file)
      * ``DEBUG_ENTRY`` → alternative debug entry point

    :param name: Application name.
    :param protocol: Custom protocol string.
    :param entry: Path or identifier for the main entry.
    :param debug_entry: Path or identifier for the debug entry.
    :return: A copy of the updated environment dictionary.
    """
    env = os.environ.copy()

    if name is not None:
        env["NAME"] = name
    if protocol is not None:
        env["PROTOCOL"] = protocol
    if entry is not None:
        env["ENTRY"] = entry
    if debug_entry is not None:
        env["DEBUG_ENTRY"] = debug_entry

    return env
