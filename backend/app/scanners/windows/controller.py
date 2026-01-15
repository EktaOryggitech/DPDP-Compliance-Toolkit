"""
DPDP GUI Compliance Scanner - Windows Application Controller

Uses pywinauto for UI automation of Windows desktop applications.
"""
import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import sys

# Windows-specific imports (conditional)
if sys.platform == "win32":
    try:
        from pywinauto import Application, Desktop
        from pywinauto.controls.uiawrapper import UIAWrapper
        PYWINAUTO_AVAILABLE = True
    except ImportError:
        PYWINAUTO_AVAILABLE = False
else:
    PYWINAUTO_AVAILABLE = False


@dataclass
class WindowElement:
    """Represents a UI element in a Windows application."""
    control_type: str
    name: str
    automation_id: str
    class_name: str
    text: str
    rect: Dict[str, int]
    is_enabled: bool
    is_visible: bool
    children: List["WindowElement"] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WindowInfo:
    """Information about a Windows window."""
    handle: int
    title: str
    class_name: str
    rect: Dict[str, int]
    elements: List[WindowElement] = field(default_factory=list)


class WindowsController:
    """
    Controller for Windows desktop application automation.

    Uses pywinauto to:
    - Launch applications
    - Enumerate windows and controls
    - Navigate through UI
    - Extract text and properties
    """

    def __init__(
        self,
        executable_path: Optional[str] = None,
        app_title: Optional[str] = None,
        backend: str = "uia",  # 'uia' or 'win32'
    ):
        if not PYWINAUTO_AVAILABLE:
            raise RuntimeError(
                "pywinauto is not available. Windows scanning is only supported on Windows."
            )

        self.executable_path = executable_path
        self.app_title = app_title
        self.backend = backend
        self._app: Optional[Application] = None
        self._main_window = None

    async def launch(self) -> bool:
        """Launch the application and wait for it to be ready."""
        if not self.executable_path:
            raise ValueError("executable_path is required to launch application")

        def _launch():
            self._app = Application(backend=self.backend).start(
                self.executable_path,
                timeout=30,
            )
            # Wait for main window
            if self.app_title:
                self._main_window = self._app.window(title_re=self.app_title)
            else:
                self._main_window = self._app.top_window()

            self._main_window.wait("visible", timeout=30)
            return True

        return await asyncio.to_thread(_launch)

    async def connect(self) -> bool:
        """Connect to an already running application."""
        def _connect():
            if self.app_title:
                self._app = Application(backend=self.backend).connect(
                    title_re=self.app_title
                )
            elif self.executable_path:
                self._app = Application(backend=self.backend).connect(
                    path=self.executable_path
                )
            else:
                raise ValueError("app_title or executable_path required")

            self._main_window = self._app.top_window()
            return True

        return await asyncio.to_thread(_connect)

    async def close(self):
        """Close the application."""
        if self._app:
            def _close():
                try:
                    self._app.kill()
                except Exception:
                    pass

            await asyncio.to_thread(_close)

    async def enumerate_windows(self) -> List[WindowInfo]:
        """Get all windows of the application."""
        def _enumerate():
            windows = []
            if not self._app:
                return windows

            for window in self._app.windows():
                try:
                    rect = window.rectangle()
                    windows.append(WindowInfo(
                        handle=window.handle,
                        title=window.window_text(),
                        class_name=window.class_name(),
                        rect={
                            "left": rect.left,
                            "top": rect.top,
                            "right": rect.right,
                            "bottom": rect.bottom,
                        },
                    ))
                except Exception:
                    continue

            return windows

        return await asyncio.to_thread(_enumerate)

    async def get_window_elements(self, window: WindowInfo) -> List[WindowElement]:
        """Get all UI elements in a window."""
        def _get_elements():
            elements = []
            if not self._app:
                return elements

            try:
                win = self._app.window(handle=window.handle)
                for ctrl in win.descendants():
                    try:
                        element = self._extract_element(ctrl)
                        if element:
                            elements.append(element)
                    except Exception:
                        continue
            except Exception:
                pass

            return elements

        return await asyncio.to_thread(_get_elements)

    def _extract_element(self, ctrl) -> Optional[WindowElement]:
        """Extract element information from a control."""
        try:
            rect = ctrl.rectangle()
            return WindowElement(
                control_type=ctrl.element_info.control_type or "Unknown",
                name=ctrl.element_info.name or "",
                automation_id=ctrl.element_info.automation_id or "",
                class_name=ctrl.element_info.class_name or "",
                text=self._get_control_text(ctrl),
                rect={
                    "left": rect.left,
                    "top": rect.top,
                    "right": rect.right,
                    "bottom": rect.bottom,
                    "width": rect.width(),
                    "height": rect.height(),
                },
                is_enabled=ctrl.is_enabled(),
                is_visible=ctrl.is_visible(),
                properties=self._get_control_properties(ctrl),
            )
        except Exception:
            return None

    def _get_control_text(self, ctrl) -> str:
        """Get text from a control using various methods."""
        try:
            # Try window_text first
            text = ctrl.window_text()
            if text:
                return text

            # Try texts() method
            texts = ctrl.texts()
            if texts:
                return " ".join(texts)

            return ""
        except Exception:
            return ""

    def _get_control_properties(self, ctrl) -> Dict[str, Any]:
        """Extract relevant properties from control."""
        props = {}
        try:
            # Check for checkbox/radio state
            if hasattr(ctrl, "get_toggle_state"):
                props["checked"] = ctrl.get_toggle_state() == 1

            # Check if it's a link
            if ctrl.element_info.control_type == "Hyperlink":
                props["is_link"] = True

            # Check for button type
            if ctrl.element_info.control_type == "Button":
                props["is_button"] = True

        except Exception:
            pass

        return props

    async def find_elements_by_text(self, text: str, partial: bool = True) -> List[WindowElement]:
        """Find elements containing specific text."""
        def _find():
            results = []
            if not self._main_window:
                return results

            for ctrl in self._main_window.descendants():
                try:
                    ctrl_text = self._get_control_text(ctrl)
                    if partial and text.lower() in ctrl_text.lower():
                        element = self._extract_element(ctrl)
                        if element:
                            results.append(element)
                    elif not partial and text.lower() == ctrl_text.lower():
                        element = self._extract_element(ctrl)
                        if element:
                            results.append(element)
                except Exception:
                    continue

            return results

        return await asyncio.to_thread(_find)

    async def find_consent_elements(self) -> List[WindowElement]:
        """Find elements related to consent in the UI."""
        consent_keywords = [
            "consent", "agree", "accept", "privacy", "terms",
            "data", "personal", "permission", "allow", "deny",
            "reject", "decline", "manage", "preferences",
            # Hindi keywords
            "सहमति", "स्वीकार", "गोपनीयता", "डेटा", "अनुमति",
        ]

        all_elements = []
        for keyword in consent_keywords:
            elements = await self.find_elements_by_text(keyword)
            all_elements.extend(elements)

        # Deduplicate by automation_id
        seen = set()
        unique = []
        for el in all_elements:
            key = (el.automation_id, el.name, el.text[:50])
            if key not in seen:
                seen.add(key)
                unique.append(el)

        return unique
