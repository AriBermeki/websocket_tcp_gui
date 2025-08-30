"""
Public API entry point for the package.

Exports the main building blocks:
  * :func:`command` → decorator to register event commands
  * :func:`launch` → start the native runtime
  * :class:`Window` → window control interface
"""

from .pyinvoke import command
from .control.window import Window
from .runtime import native_runtime as launch

__all__ = ["command", "launch", "Window"]
