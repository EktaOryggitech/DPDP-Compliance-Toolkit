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

    async def annotate_element(
        self,
        screenshot: AnnotatedScreenshot,
        element_box: Dict[str, float],
        label: str = None,
        color: Tuple[int, int, int] = (255, 0, 0),  # Red
        border_width: int = 6,
    ) -> AnnotatedScreenshot:
        """
        Annotate a screenshot with a highlighted element box.

        Args:
            screenshot: The screenshot to annotate
            element_box: Bounding box dict with x, y, width, height
            label: Optional label text to add
            color: RGB color tuple for the border
            border_width: Width of the border in pixels

        Returns:
            Updated AnnotatedScreenshot with annotated_path set
        """
        if not PIL_AVAILABLE:
            print("[Screenshot] PIL not available, skipping annotation")
            return screenshot

        if not element_box:
            print("[Screenshot] No element_box provided, skipping annotation")
            return screenshot

        def _annotate():
            from PIL import ImageDraw, ImageFont

            # Open the original screenshot
            img = Image.open(screenshot.original_path)
            print(f"[Screenshot] Annotating image size: {img.size}")
            print(f"[Screenshot] Element box received: {element_box}")

            # Get box coordinates - use float values directly, convert to int for drawing
            x = int(float(element_box.get("x", 0)))
            y = int(float(element_box.get("y", 0)))
            width = int(float(element_box.get("width", 100)))
            height = int(float(element_box.get("height", 50)))

            print(f"[Screenshot] Drawing annotation at: x={x}, y={y}, width={width}, height={height}")

            # Ensure minimum dimensions for visibility
            width = max(width, 10)
            height = max(height, 10)

            # Ensure coordinates are within image bounds
            x = max(0, min(x, img.width - 10))
            y = max(0, min(y, img.height - 10))
            width = min(width, img.width - x)
            height = min(height, img.height - y)

            # Convert to RGBA for overlay
            if img.mode != "RGBA":
                img = img.convert("RGBA")

            # Create a light red semi-transparent overlay on the element area
            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)

            # Draw light red overlay on the element (semi-transparent red highlight)
            overlay_draw.rectangle(
                [x, y, x + width, y + height],
                fill=(255, 0, 0, 50)  # Light red tint
            )

            # Composite the red highlight overlay
            img = Image.alpha_composite(img, overlay)

            # Create drawing context for borders and label
            draw = ImageDraw.Draw(img)

            # Draw thick red rectangle border around the element
            for i in range(border_width):
                draw.rectangle(
                    [x - i, y - i, x + width + i, y + height + i],
                    outline=color
                )

            # Add corner markers for extra visibility
            corner_size = max(10, min(20, width // 4, height // 4))
            corner_width = 4

            # Top-left corner
            draw.line([(x, y), (x + corner_size, y)], fill=color, width=corner_width)
            draw.line([(x, y), (x, y + corner_size)], fill=color, width=corner_width)

            # Top-right corner
            draw.line([(x + width, y), (x + width - corner_size, y)], fill=color, width=corner_width)
            draw.line([(x + width, y), (x + width, y + corner_size)], fill=color, width=corner_width)

            # Bottom-left corner
            draw.line([(x, y + height), (x + corner_size, y + height)], fill=color, width=corner_width)
            draw.line([(x, y + height), (x, y + height - corner_size)], fill=color, width=corner_width)

            # Bottom-right corner
            draw.line([(x + width, y + height), (x + width - corner_size, y + height)], fill=color, width=corner_width)
            draw.line([(x + width, y + height), (x + width, y + height - corner_size)], fill=color, width=corner_width)

            # Add label if provided
            if label:
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
                except:
                    try:
                        font = ImageFont.truetype("/usr/share/fonts/liberation/LiberationSans-Bold.ttf", 18)
                    except:
                        font = ImageFont.load_default()

                # Position label above the box
                label_y = max(y - 30, 5)
                label_x = x

                # Draw label background (red box with white text)
                bbox = draw.textbbox((label_x, label_y), label, font=font)
                padding = 6
                draw.rectangle(
                    [bbox[0] - padding, bbox[1] - padding, bbox[2] + padding, bbox[3] + padding],
                    fill=color
                )
                draw.text((label_x, label_y), label, fill=(255, 255, 255), font=font)

            # Save annotated version
            annotated_id = f"{screenshot.id}_annotated"
            annotated_filename = f"{annotated_id}.jpg"
            annotated_filepath = os.path.join(self.output_dir, annotated_filename)

            # Convert back to RGB for JPEG
            if img.mode == "RGBA":
                img = img.convert("RGB")

            img.save(annotated_filepath, "JPEG", quality=settings.SCREENSHOT_QUALITY)
            print(f"[Screenshot] Annotated screenshot saved: {annotated_filepath}")

            return annotated_filepath

        try:
            annotated_path = await asyncio.to_thread(_annotate)

            # Update screenshot with annotation info
            screenshot.annotated_path = annotated_path
            screenshot.annotations.append({
                "type": "element_highlight",
                "box": element_box,
                "label": label,
                "color": color,
            })
        except Exception as e:
            print(f"[Screenshot] Error during annotation: {e}")
            import traceback
            traceback.print_exc()

        return screenshot

    async def capture_and_annotate_element(
        self,
        page: "Page",
        url: str,
        selector: str,
        label: str = "VIOLATION",
    ) -> Optional[AnnotatedScreenshot]:
        """
        Capture a viewport screenshot with the violating element highlighted.

        Shows the element IN CONTEXT with surrounding content, not just the element itself.
        The element is highlighted with a red border so it stands out.

        Args:
            page: Playwright page object
            url: URL being captured
            selector: CSS selector for the element to capture
            label: Label to show on the annotation

        Returns:
            AnnotatedScreenshot of viewport with element highlighted, or None if element not found
        """
        try:
            print(f"[Screenshot] Looking for element: {selector}")

            # First, try to find the element
            element = await page.query_selector(selector)
            if not element:
                print(f"[Screenshot] Element not found: {selector} - skipping screenshot")
                return None

            # Scroll element into view (centered if possible)
            try:
                await element.scroll_into_view_if_needed()
                await asyncio.sleep(0.3)
            except Exception as scroll_error:
                print(f"[Screenshot] Scroll error (continuing): {scroll_error}")

            # Get element bounding box
            bounding_box = await element.bounding_box()
            if not bounding_box:
                print(f"[Screenshot] Could not get bounding box for: {selector} - skipping screenshot")
                return None

            print(f"[Screenshot] Element bounding box: {bounding_box}")

            # Inject CSS to highlight the element with a red border
            try:
                # Add highlight to the element using JavaScript
                await element.evaluate('''el => {
                    el.style.outline = "4px solid red";
                    el.style.outlineOffset = "2px";
                    el.style.boxShadow = "0 0 15px 5px rgba(255, 0, 0, 0.6)";
                }''')
                await asyncio.sleep(0.3)  # Wait for style to apply
                print(f"[Screenshot] Applied red highlight to element")
            except Exception as style_error:
                print(f"[Screenshot] Could not apply highlight style: {style_error}")

            # Capture viewport screenshot (shows element in context)
            screenshot_id = str(uuid.uuid4())
            filename = f"{screenshot_id}.jpg"
            filepath = os.path.join(self.output_dir, filename)

            try:
                # Take viewport screenshot (not full page, not just element)
                await page.screenshot(
                    path=filepath,
                    type="jpeg",
                    quality=settings.SCREENSHOT_QUALITY,
                    full_page=False  # Just the visible viewport
                )
                print(f"[Screenshot] Viewport screenshot captured with highlighted element: {filepath}")
            except Exception as screenshot_error:
                print(f"[Screenshot] Viewport screenshot failed: {screenshot_error} - skipping")
                return None

            # Try to remove the highlight (cleanup)
            try:
                await element.evaluate('el => { el.style.outline = ""; el.style.outlineOffset = ""; el.style.boxShadow = ""; }')
            except:
                pass  # Ignore cleanup errors

            # Get viewport size for metadata
            viewport = page.viewport_size or {"width": 1920, "height": 1080}

            screenshot = AnnotatedScreenshot(
                id=screenshot_id,
                original_path=filepath,
                annotated_path=filepath,  # Already annotated via CSS highlight
                url_or_window=url,
                timestamp=datetime.utcnow(),
                width=viewport["width"],
                height=viewport["height"],
                metadata={
                    "type": "viewport_with_highlight",
                    "selector": selector,
                    "element_bounding_box": bounding_box,
                },
            )

            return screenshot

        except Exception as e:
            print(f"[Screenshot] Error capturing element screenshot: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def _add_red_border(
        self,
        screenshot: AnnotatedScreenshot,
        label: str = "VIOLATION",
        border_width: int = 8,
        color: Tuple[int, int, int] = (255, 0, 0),
    ) -> AnnotatedScreenshot:
        """
        Add a red border and label around a screenshot.

        Args:
            screenshot: The screenshot to add border to
            label: Label text to add
            border_width: Width of the red border
            color: RGB color tuple for the border

        Returns:
            Screenshot with red border added
        """
        if not PIL_AVAILABLE:
            return screenshot

        def _add_border():
            from PIL import ImageDraw, ImageFont, ImageOps

            # Open the original screenshot
            img = Image.open(screenshot.original_path)
            print(f"[Screenshot] Adding red border to image: {img.size}")

            # Add red border around the entire image
            img_with_border = ImageOps.expand(img, border=border_width, fill=color)

            # Create drawing context
            draw = ImageDraw.Draw(img_with_border)

            # Add label at the top
            if label:
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
                except:
                    try:
                        font = ImageFont.truetype("/usr/share/fonts/liberation/LiberationSans-Bold.ttf", 16)
                    except:
                        font = ImageFont.load_default()

                # Get text size
                bbox = draw.textbbox((0, 0), label, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]

                # Create label background at top-left
                padding = 4
                label_bg_height = text_height + padding * 2
                draw.rectangle(
                    [0, 0, text_width + padding * 2, label_bg_height],
                    fill=color
                )
                draw.text((padding, padding), label, fill=(255, 255, 255), font=font)

            # Save the bordered version
            annotated_id = f"{screenshot.id}_bordered"
            annotated_filename = f"{annotated_id}.jpg"
            annotated_filepath = os.path.join(self.output_dir, annotated_filename)

            # Convert to RGB if needed
            if img_with_border.mode != "RGB":
                img_with_border = img_with_border.convert("RGB")

            img_with_border.save(annotated_filepath, "JPEG", quality=settings.SCREENSHOT_QUALITY)
            print(f"[Screenshot] Bordered screenshot saved: {annotated_filepath}")

            return annotated_filepath

        try:
            annotated_path = await asyncio.to_thread(_add_border)
            screenshot.annotated_path = annotated_path
            screenshot.annotations.append({
                "type": "red_border",
                "label": label,
                "border_width": border_width,
                "color": color,
            })
        except Exception as e:
            print(f"[Screenshot] Error adding border: {e}")
            import traceback
            traceback.print_exc()

        return screenshot
