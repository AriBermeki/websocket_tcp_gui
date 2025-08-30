from typing import Any, Dict, Optional, Tuple
from ..runtime_handle import eventloop_event_register_typed


class Window:
    """
    Asynchronous API wrapper for window management.

    Provides methods to query and control a window via the
    event loop backend. Each method sends a request to the
    Rust runtime and returns the result.
    """

    def __init__(self):
        """Initialize a new window reference with default label ``"root"``."""
        self.label: str = "root"

    async def window_query(self, label: str) -> "Window":
        """
        Change the active window label.

        :param label: Identifier of the target window.
        :return: Self, updated with the new label.
        """
        self.label = label
        return self

    async def title(self) -> str:
        """
        Get the window title.

        :return: Current window title.
        """
        return await eventloop_event_register_typed("window.title", {"label": self.label}, result_type=str)

    async def is_fullscreen(self) -> bool:
        """Check if the window is in fullscreen mode."""
        return await eventloop_event_register_typed("window.isFullscreen", {"label": self.label}, result_type=bool)

    async def is_minimized(self) -> bool:
        """Check if the window is minimized."""
        return await eventloop_event_register_typed("window.isMinimized", {"label": self.label}, result_type=bool)

    async def is_maximized(self) -> bool:
        """Check if the window is maximized."""
        return await eventloop_event_register_typed("window.isMaximized", {"label": self.label}, result_type=bool)

    async def is_focused(self) -> bool:
        """Check if the window currently has input focus."""
        return await eventloop_event_register_typed("window.isFocused", {"label": self.label}, result_type=bool)

    async def is_visible(self) -> bool:
        """Check if the window is visible."""
        return await eventloop_event_register_typed("window.isVisible", {"label": self.label}, result_type=bool)

    async def scale_factor(self) -> float:
        """Get the current display scale factor of the window."""
        return await eventloop_event_register_typed("window.scaleFactor", {"label": self.label}, result_type=float)

    async def inner_size(self) -> Tuple[int, int]:
        """Get the inner (content) size of the window as ``(width, height)``."""
        return await eventloop_event_register_typed("window.innerSize", {"label": self.label}, result_type=Tuple[int, int])

    async def outer_size(self) -> Tuple[int, int]:
        """Get the outer (frame) size of the window as ``(width, height)``."""
        return await eventloop_event_register_typed("window.outerSize", {"label": self.label}, result_type=Tuple[int, int])

    async def current_monitor(self) -> Optional[Dict[str, Any]]:
        """Get information about the monitor displaying this window."""
        return await eventloop_event_register_typed("window.currentMonitor", {"label": self.label}, result_type=Optional[Dict[str, Any]])

    async def primary_monitor(self) -> Optional[Dict[str, Any]]:
        """Get information about the primary monitor of the system."""
        return await eventloop_event_register_typed("window.primaryMonitor", {"label": self.label}, result_type=Optional[Dict[str, Any]])

    async def theme(self) -> Optional[str]:
        """Get the current theme applied to the window (e.g. ``light`` or ``dark``)."""
        return await eventloop_event_register_typed("window.theme", {"label": self.label}, result_type=Optional[str])

    async def set_title(self, title: str) -> bool:
        """
        Set the window title.

        :param title: New window title.
        :return: ``True`` if the operation succeeded.
        """
        return await eventloop_event_register_typed("set_title", title, result_type=bool)

    async def set_fullscreen(self, fullscreen: bool) -> bool:
        """
        Enable or disable fullscreen mode.

        :param fullscreen: ``True`` to enter fullscreen, ``False`` to exit.
        :return: ``True`` if the operation succeeded.
        """
        return await eventloop_event_register_typed("window.setFullscreen", {"label": self.label, "fullscreen": fullscreen})

    async def set_visible(self, visible: bool) -> bool:
        """
        Show or hide the window.

        :param visible: ``True`` to show, ``False`` to hide.
        :return: ``True`` if the operation succeeded.
        """
        method = "window.show" if visible else "window.hide"
        return await eventloop_event_register_typed(method, {"label": self.label}, result_type=bool)

    async def maximize(self) -> bool:
        """Maximize the window."""
        return await eventloop_event_register_typed("window.maximize", {"label": self.label}, result_type=bool)

    async def minimize(self) -> bool:
        """Minimize the window."""
        return await eventloop_event_register_typed("window.minimize", {"label": self.label}, result_type=bool)

    async def unmaximize(self) -> bool:
        """Restore the window from maximized state."""
        return await eventloop_event_register_typed("window.unmaximize", {"label": self.label}, result_type=bool)

    async def unminimize(self) -> bool:
        """Restore the window from minimized state."""
        return await eventloop_event_register_typed("window.unminimize", {"label": self.label}, result_type=bool)

    async def close(self) -> bool:
        """Close the window."""
        return await eventloop_event_register_typed("window.close", {"label": self.label}, result_type=bool)

    async def destroy(self) -> bool:
        """Destroy the window and free its resources."""
        return await eventloop_event_register_typed("window.destroy", {"label": self.label}, result_type=bool)

    async def center(self) -> bool:
        """Center the window on its current monitor."""
        return await eventloop_event_register_typed("window.center", {"label": self.label}, result_type=bool)

    async def set_resizable(self, resizable: bool) -> bool:
        """
        Set whether the window can be resized.

        :param resizable: ``True`` to allow resizing.
        :return: ``True`` if the operation succeeded.
        """
        return await eventloop_event_register_typed("window.setResizable", {"label": self.label, "resizable": resizable}, result_type=bool)

    async def set_always_on_top(self, always: bool) -> bool:
        """
        Set the window to always stay on top of other windows.

        :param always: ``True`` to enable always-on-top.
        :return: ``True`` if the operation succeeded.
        """
        return await eventloop_event_register_typed("window.setAlwaysOnTop", {"label": self.label, "alwaysOnTop": always}, result_type=bool)

    async def request_redraw(self) -> bool:
        """Request a redraw of the window contents."""
        return await eventloop_event_register_typed("window.requestRedraw", {"label": self.label}, result_type=bool)

    async def set_focus(self) -> bool:
        """Bring the window into focus."""
        return await eventloop_event_register_typed("window.setFocus", {"label": self.label}, result_type=bool)
