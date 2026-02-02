"""
DPDP GUI Compliance Scanner - Violation Screenshot Service

Captures annotated screenshots for compliance violations.
Re-visits pages and highlights the violating elements.
"""
import asyncio
import traceback
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from app.core.config import settings
from app.evidence.screenshot import ScreenshotCapture, AnnotatedScreenshot
from app.evidence.storage import EvidenceStorage, StoredEvidence, MINIO_AVAILABLE
from app.models.finding import FindingSeverity


@dataclass
class ViolationScreenshotResult:
    """Result of capturing a violation screenshot."""
    finding_id: str
    success: bool
    storage_path: Optional[str] = None
    presigned_url: Optional[str] = None
    error: Optional[str] = None


class ViolationScreenshotService:
    """
    Service for capturing screenshots of compliance violations.

    Features:
    - Re-visits pages to capture current state
    - Highlights violating elements with red borders
    - Uploads to MinIO storage
    - Generates presigned URLs for viewing
    - Only captures for Critical and High severity findings
    """

    # Severity levels that require screenshots
    SCREENSHOT_SEVERITIES = [FindingSeverity.CRITICAL, FindingSeverity.HIGH]

    def __init__(self):
        self.screenshot_capture = ScreenshotCapture()
        self.storage: Optional[EvidenceStorage] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    async def initialize(self):
        """Initialize the browser and storage."""
        print(f"[ViolationScreenshot] Initializing... MinIO available: {MINIO_AVAILABLE}")
        print(f"[ViolationScreenshot] MinIO endpoint: {settings.MINIO_ENDPOINT}")

        if not MINIO_AVAILABLE:
            print("[ViolationScreenshot] WARNING: MinIO package not available - screenshots will use local storage only")
            self.storage = None
            return

        try:
            self.storage = EvidenceStorage()
            print(f"[ViolationScreenshot] Storage initialized successfully, bucket: {self.storage.bucket_name}")
        except Exception as e:
            print(f"[ViolationScreenshot] ERROR: Could not initialize storage: {e}")
            print(f"[ViolationScreenshot] Traceback: {traceback.format_exc()}")
            self.storage = None

    async def _ensure_browser(self):
        """Ensure browser is running."""
        if not self._browser:
            playwright = await async_playwright().start()
            self._browser = await playwright.chromium.launch(
                headless=True,
                args=["--disable-web-security"]
            )
            self._context = await self._browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="DPDP Compliance Scanner/1.0",
                ignore_https_errors=True,
            )

    async def close(self):
        """Close browser and cleanup."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        self.screenshot_capture.cleanup()

    def should_capture_screenshot(self, severity: FindingSeverity) -> bool:
        """Check if a finding severity warrants a screenshot."""
        return severity in self.SCREENSHOT_SEVERITIES

    async def capture_violation_screenshot(
        self,
        scan_id: str,
        finding_id: str,
        page_url: str,
        element_selector: Optional[str],
        violation_title: str,
        auth_config: Optional[Dict] = None,
    ) -> ViolationScreenshotResult:
        """
        Capture a screenshot of a violation.

        Args:
            scan_id: The scan ID
            finding_id: The finding ID
            page_url: URL of the page with the violation
            element_selector: CSS selector of the violating element
            violation_title: Title/label for the annotation
            auth_config: Optional authentication configuration

        Returns:
            ViolationScreenshotResult with storage path or error
        """
        try:
            print(f"[ViolationScreenshot] Capturing screenshot for finding {finding_id[:8]}...")
            print(f"[ViolationScreenshot] Original URL: {page_url}")
            print(f"[ViolationScreenshot] Selector: {element_selector}")

            # Convert localhost URLs to Docker-accessible URLs
            original_url = page_url
            if page_url:
                page_url = page_url.replace("localhost", "host.docker.internal")
                page_url = page_url.replace("127.0.0.1", "host.docker.internal")
                if page_url != original_url:
                    print(f"[ViolationScreenshot] Converted URL: {page_url}")

            await self._ensure_browser()

            # Create a new page
            page = await self._context.new_page()

            try:
                # Handle authentication if needed
                if auth_config and auth_config.get("auth_type") != "none":
                    await self._handle_auth(page, auth_config)

                # Navigate to the page with retry logic
                nav_success = False
                for attempt in range(3):
                    for wait_strategy in ['domcontentloaded', 'load', 'networkidle']:
                        try:
                            timeout = 90000 * (1 + attempt * 0.5)  # 90s, 135s, 180s
                            await page.goto(
                                page_url,
                                wait_until=wait_strategy,
                                timeout=timeout
                            )
                            nav_success = True
                            break
                        except Exception as nav_error:
                            print(f"[ViolationScreenshot] Navigation attempt {attempt+1} with {wait_strategy} failed: {nav_error}")
                            continue
                    if nav_success:
                        break

                if not nav_success:
                    return ViolationScreenshotResult(
                        finding_id=finding_id,
                        success=False,
                        error="Failed to navigate to page after multiple attempts"
                    )

                # Wait for page to settle
                await page.wait_for_timeout(2000)

                # Capture screenshot with annotation
                if element_selector:
                    screenshot = await self.screenshot_capture.capture_and_annotate_element(
                        page=page,
                        url=page_url,
                        selector=element_selector,
                        label=violation_title[:30] if violation_title else "VIOLATION"
                    )
                else:
                    # No selector - just capture full page
                    screenshot = await self.screenshot_capture.capture_web_page(
                        page=page,
                        url=page_url,
                        full_page=True
                    )

                if not screenshot:
                    print(f"[ViolationScreenshot] ERROR: Failed to capture screenshot for {finding_id[:8]}")
                    return ViolationScreenshotResult(
                        finding_id=finding_id,
                        success=False,
                        error="Failed to capture screenshot"
                    )

                print(f"[ViolationScreenshot] Screenshot captured: {screenshot.annotated_path or screenshot.original_path}")

                # Upload to storage
                if self.storage:
                    try:
                        print(f"[ViolationScreenshot] Uploading to MinIO...")
                        stored = await self.storage.upload_screenshot(
                            screenshot=screenshot,
                            scan_id=scan_id,
                            finding_id=finding_id
                        )

                        # Generate presigned URL
                        presigned_url = await self.storage.get_presigned_url(
                            stored.file_path,
                            expires_hours=72  # 3 days
                        )

                        print(f"[ViolationScreenshot] SUCCESS: Screenshot saved to MinIO: {stored.file_path}")

                        return ViolationScreenshotResult(
                            finding_id=finding_id,
                            success=True,
                            storage_path=stored.file_path,
                            presigned_url=presigned_url
                        )
                    except Exception as upload_error:
                        print(f"[ViolationScreenshot] ERROR uploading to MinIO: {upload_error}")
                        print(f"[ViolationScreenshot] Traceback: {traceback.format_exc()}")
                        # Fall through to return local path
                        return ViolationScreenshotResult(
                            finding_id=finding_id,
                            success=False,
                            error=f"Upload failed: {str(upload_error)}"
                        )
                else:
                    # No storage configured - this is a problem for the API
                    print(f"[ViolationScreenshot] WARNING: No storage configured, screenshot at local path only")
                    return ViolationScreenshotResult(
                        finding_id=finding_id,
                        success=False,
                        error="Storage not available - screenshot captured but cannot be served",
                    )

            finally:
                await page.close()

        except Exception as e:
            print(f"[ViolationScreenshot] Error capturing screenshot: {e}")
            return ViolationScreenshotResult(
                finding_id=finding_id,
                success=False,
                error=str(e)
            )

    async def _handle_auth(self, page: Page, auth_config: Dict):
        """Handle authentication for the page."""
        auth_type = auth_config.get("auth_type")

        if auth_type == "basic":
            credentials = auth_config.get("credentials", {})
            await page.context.set_http_credentials({
                "username": credentials.get("username", ""),
                "password": credentials.get("password", ""),
            })

        elif auth_type == "cookie" or auth_type == "session":
            cookies = auth_config.get("session_cookies") or auth_config.get("cookies", [])
            if cookies:
                await page.context.add_cookies(cookies)

        # Form-based auth would need full login flow - skip for now
        # as the original crawl session should have handled it

    async def capture_batch_screenshots(
        self,
        scan_id: str,
        findings: List[Dict[str, Any]],
        auth_config: Optional[Dict] = None,
        max_concurrent: int = 3,
    ) -> List[ViolationScreenshotResult]:
        """
        Capture screenshots for multiple findings.

        Args:
            scan_id: The scan ID
            findings: List of finding dicts with id, location, element_selector, title, severity
            auth_config: Optional authentication configuration
            max_concurrent: Maximum concurrent screenshot captures

        Returns:
            List of ViolationScreenshotResult
        """
        # Filter to only Critical and High severity
        eligible_findings = [
            f for f in findings
            if self.should_capture_screenshot(
                FindingSeverity(f.get("severity")) if isinstance(f.get("severity"), str)
                else f.get("severity")
            )
        ]

        print(f"[ViolationScreenshot] === Starting batch screenshot capture ===")
        print(f"[ViolationScreenshot] Total findings: {len(findings)}")
        print(f"[ViolationScreenshot] Eligible (Critical/High): {len(eligible_findings)}")

        if not eligible_findings:
            print("[ViolationScreenshot] No eligible findings for screenshot capture")
            return []

        # Log each eligible finding
        for i, f in enumerate(eligible_findings):
            print(f"[ViolationScreenshot] Finding {i+1}: {f.get('id', 'no-id')[:8]} - {f.get('severity')} - {f.get('location', 'no-url')[:50]}")

        await self.initialize()

        results = []
        semaphore = asyncio.Semaphore(max_concurrent)

        async def capture_with_limit(finding: Dict) -> ViolationScreenshotResult:
            async with semaphore:
                return await self.capture_violation_screenshot(
                    scan_id=scan_id,
                    finding_id=str(finding.get("id")),
                    page_url=finding.get("location", ""),
                    element_selector=finding.get("element_selector"),
                    violation_title=finding.get("title", "Violation"),
                    auth_config=auth_config,
                )

        # Capture screenshots concurrently with limit
        tasks = [capture_with_limit(f) for f in eligible_findings]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(ViolationScreenshotResult(
                    finding_id=str(eligible_findings[i].get("id")),
                    success=False,
                    error=str(result)
                ))
            else:
                final_results.append(result)

        await self.close()

        success_count = sum(1 for r in final_results if r.success)
        failed_count = len(final_results) - success_count

        print(f"[ViolationScreenshot] === Batch capture complete ===")
        print(f"[ViolationScreenshot] Success: {success_count}, Failed: {failed_count}")

        # Log details of each result
        for r in final_results:
            if r.success:
                print(f"[ViolationScreenshot] ✓ {r.finding_id[:8]}: {r.storage_path}")
            else:
                print(f"[ViolationScreenshot] ✗ {r.finding_id[:8]}: {r.error}")

        return final_results
