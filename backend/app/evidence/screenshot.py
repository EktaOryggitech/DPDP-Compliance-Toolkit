"""
DPDP GUI Compliance Scanner - Screenshot Capture Module

Captures screenshots from web and Windows applications.
"""
import asyncio
import base64
import io
import os
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from PIL import Image
    from playwright.async_api import Page
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from app.core.config import settings


@dataclass
class AnnotatedScreenshot:
    """Screenshot with annotations."""
    id: str
    original_path: str
    annotated_path: Optional[str]
    url_or_window: str
    timestamp: datetime
    width: int
    height: int
    annotations: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_base64(self, annotated: bool = True) -> str:
        """Convert screenshot to base64 string."""
        path = self.annotated_path if annotated and self.annotated_path else self.original_path

        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")


class ScreenshotCapture:
    """
    Screenshot capture utility for evidence collection.

    Supports:
    - Full page web screenshots via Playwright
    - Window screenshots via Win32 API
    - Region/element screenshots
    - Screenshot annotations
    """

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or tempfile.mkdtemp(prefix="dpdp_screenshots_")
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    async def capture_web_page(
        self,
        page: "Page",
        url: str,
        full_page: bool = True,
        quality: int = None,
    ) -> AnnotatedScreenshot:
        """
        Capture screenshot of a web page using Playwright.

        Args:
            page: Playwright page object
            url: URL being captured (for metadata)
            full_page: Whether to capture full scrollable page
            quality: JPEG quality (1-100)

        Returns:
            AnnotatedScreenshot with path to saved image
        """
        quality = quality or settings.SCREENSHOT_QUALITY

        screenshot_id = str(uuid.uuid4())
        filename = f"{screenshot_id}.jpg"
        filepath = os.path.join(self.output_dir, filename)

        # Capture screenshot
        await page.screenshot(
            path=filepath,
            full_page=full_page,
            quality=quality,
            type="jpeg",
        )

        # Get page dimensions
        viewport = page.viewport_size
        width = viewport["width"] if viewport else 1920
        height = viewport["height"] if viewport else 1080

        if full_page:
            # Get actual page height
            height = await page.evaluate("document.documentElement.scrollHeight")

        return AnnotatedScreenshot(
            id=screenshot_id,
            original_path=filepath,
            annotated_path=None,
            url_or_window=url,
            timestamp=datetime.utcnow(),
            width=width,
            height=height,
            metadata={
                "type": "web",
                "full_page": full_page,
                "quality": quality,
            },
        )

    async def capture_web_element(
        self,
        page: "Page",
        selector: str,
        url: str,
    ) -> Optional[AnnotatedScreenshot]:
        """
        Capture screenshot of a specific web element.

        Args:
            page: Playwright page object
            selector: CSS selector for the element
            url: URL being captured

        Returns:
            AnnotatedScreenshot or None if element not found
        """
        try:
            element = await page.query_selector(selector)
            if not element:
                return None

            screenshot_id = str(uuid.uuid4())
            filename = f"{screenshot_id}_element.jpg"
            filepath = os.path.join(self.output_dir, filename)

            await element.screenshot(path=filepath, type="jpeg")

            bounding_box = await element.bounding_box()

            return AnnotatedScreenshot(
                id=screenshot_id,
                original_path=filepath,
                annotated_path=None,
                url_or_window=url,
                timestamp=datetime.utcnow(),
                width=int(bounding_box["width"]) if bounding_box else 0,
                height=int(bounding_box["height"]) if bounding_box else 0,
                metadata={
                    "type": "web_element",
                    "selector": selector,
                    "bounding_box": bounding_box,
                },
            )

        except Exception as e:
            print(f"Error capturing element {selector}: {e}")
            return None

    async def capture_windows_screen(
        self,
        window_handle: int = None,
        window_title: str = None,
    ) -> AnnotatedScreenshot:
        """
        Capture screenshot of a Windows window or desktop.

        Args:
            window_handle: Win32 window handle
            window_title: Window title for metadata

        Returns:
            AnnotatedScreenshot with captured image
        """
        import sys
        if sys.platform != "win32":
            raise RuntimeError("Windows screenshot capture only available on Windows")

        def _capture():
            import win32gui
            import win32ui
            import win32con
            from ctypes import windll

            # Get window or desktop dimensions
            if window_handle:
                left, top, right, bottom = win32gui.GetWindowRect(window_handle)
            else:
                # Full desktop
                left = win32gui.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
                top = win32gui.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)
                right = left + win32gui.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
                bottom = top + win32gui.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)

            width = right - left
            height = bottom - top

            # Create DC and bitmap
            if window_handle:
                hwnd_dc = win32gui.GetWindowDC(window_handle)
            else:
                hwnd_dc = win32gui.GetDC(0)

            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()
            save_bitmap = win32ui.CreateBitmap()
            save_bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
            save_dc.SelectObject(save_bitmap)

            # Capture
            if window_handle:
                windll.user32.PrintWindow(window_handle, save_dc.GetSafeHdc(), 2)
            else:
                save_dc.BitBlt((0, 0), (width, height), mfc_dc, (left, top), win32con.SRCCOPY)

            # Convert to PIL Image
            bmp_info = save_bitmap.GetInfo()
            bmp_bits = save_bitmap.GetBitmapBits(True)

            img = Image.frombuffer(
                "RGB",
                (bmp_info["bmWidth"], bmp_info["bmHeight"]),
                bmp_bits, "raw", "BGRX", 0, 1
            )

            # Save
            screenshot_id = str(uuid.uuid4())
            filename = f"{screenshot_id}_windows.jpg"
            filepath = os.path.join(self.output_dir, filename)
            img.save(filepath, "JPEG", quality=settings.SCREENSHOT_QUALITY)

            # Cleanup
            win32gui.DeleteObject(save_bitmap.GetHandle())
            save_dc.DeleteDC()
            mfc_dc.DeleteDC()
            win32gui.ReleaseDC(window_handle or 0, hwnd_dc)

            return AnnotatedScreenshot(
                id=screenshot_id,
                original_path=filepath,
                annotated_path=None,
                url_or_window=window_title or f"Window:{window_handle}",
                timestamp=datetime.utcnow(),
                width=width,
                height=height,
                metadata={
                    "type": "windows",
                    "window_handle": window_handle,
                },
            )

        return await asyncio.to_thread(_capture)

    async def capture_region(
        self,
        page_or_handle: Any,
        region: Tuple[int, int, int, int],
        source_url: str,
    ) -> AnnotatedScreenshot:
        """
        Capture a specific region of a page/window.

        Args:
            page_or_handle: Playwright page or window handle
            region: (x, y, width, height) tuple
            source_url: URL or window identifier

        Returns:
            AnnotatedScreenshot of the region
        """
        x, y, width, height = region

        # First capture full screenshot
        if hasattr(page_or_handle, "screenshot"):
            # Playwright page
            full_screenshot = await self.capture_web_page(
                page_or_handle, source_url, full_page=False
            )
        else:
            # Windows handle
            full_screenshot = await self.capture_windows_screen(
                page_or_handle, source_url
            )

        # Crop to region
        def _crop():
            img = Image.open(full_screenshot.original_path)
            cropped = img.crop((x, y, x + width, y + height))

            screenshot_id = str(uuid.uuid4())
            filename = f"{screenshot_id}_region.jpg"
            filepath = os.path.join(self.output_dir, filename)
            cropped.save(filepath, "JPEG", quality=settings.SCREENSHOT_QUALITY)

            return AnnotatedScreenshot(
                id=screenshot_id,
                original_path=filepath,
                annotated_path=None,
                url_or_window=source_url,
                timestamp=datetime.utcnow(),
                width=width,
                height=height,
                metadata={
                    "type": "region",
                    "region": region,
                },
            )

        return await asyncio.to_thread(_crop)

    def cleanup(self):
        """Clean up temporary screenshot files."""
        import shutil
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir, ignore_errors=True)
