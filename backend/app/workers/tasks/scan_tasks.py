"""
DPDP GUI Compliance Scanner - Scan Tasks

Celery tasks for running compliance scans with real-time WebSocket progress updates.
"""
import asyncio
import uuid
from datetime import datetime
from typing import Optional, List

from celery import current_task
from sqlalchemy import select

from app.core.database import async_session_maker
from app.core.config import settings
from app.core.websocket import ScanProgressReporter
from app.models.application import Application, ApplicationType
from app.models.scan import Scan, ScanStatus, ScanType
from app.models.finding import Finding, FindingSeverity, FindingStatus, CheckType
from app.models.scan_configuration import ScanConfiguration
from app.workers.celery_app import celery_app


def update_task_progress(current: int, total: int, message: str):
    """Update Celery task progress for real-time monitoring."""
    current_task.update_state(
        state="PROGRESS",
        meta={
            "current": current,
            "total": total,
            "message": message,
            "percent": int((current / total) * 100) if total > 0 else 0,
        },
    )


async def create_progress_reporter(scan_id: str) -> ScanProgressReporter:
    """Create and connect a progress reporter for WebSocket updates."""
    reporter = ScanProgressReporter(scan_id, settings.REDIS_URL)
    await reporter.connect()
    return reporter


async def get_scan_configuration_from_db(db) -> Optional[dict]:
    """Fetch scan configuration from database."""
    result = await db.execute(select(ScanConfiguration).limit(1))
    config = result.scalar_one_or_none()

    if config:
        return {
            "quick_pages": config.quick_pages,
            "standard_pages": config.standard_pages,
            "deep_pages": config.deep_pages,
        }
    return None


@celery_app.task(bind=True, name="app.workers.tasks.scan_tasks.run_web_scan")
def run_web_scan(self, scan_id: str, application_id: str):
    """
    Execute a web application compliance scan.

    This task:
    1. Crawls the target website
    2. Captures screenshots of each page
    3. Extracts DOM content for analysis
    4. Runs all compliance detectors
    5. Stores findings and evidence
    """
    try:
        return asyncio.get_event_loop().run_until_complete(
            _run_web_scan_async(self, scan_id, application_id)
        )
    except Exception as e:
        # Handle timeout and other exceptions that escape the async handler
        # This ensures scan status is updated even for Celery timeouts
        error_message = str(e)
        if "SoftTimeLimitExceeded" in type(e).__name__ or "TimeLimitExceeded" in type(e).__name__:
            error_message = "Scan timed out. Try reducing the number of pages or using a Quick scan."

        # Update scan status synchronously
        try:
            import asyncio as aio
            loop = aio.new_event_loop()
            loop.run_until_complete(_mark_scan_failed(scan_id, error_message))
            loop.close()
        except Exception as update_error:
            print(f"[SCAN] Failed to update scan status: {update_error}")

        raise


async def _mark_scan_failed(scan_id: str, error_message: str):
    """Mark a scan as failed in the database."""
    async with async_session_maker() as db:
        scan = await db.get(Scan, uuid.UUID(scan_id))
        if scan and scan.status == ScanStatus.RUNNING:
            scan.status = ScanStatus.FAILED
            scan.status_message = error_message
            scan.completed_at = datetime.utcnow()
            await db.commit()
            print(f"[SCAN] Marked scan {scan_id} as FAILED: {error_message}")


def calculate_timeout(pages: int) -> int:
    """
    Calculate timeout based on page count.

    Formula: timeout = (180 + pages × 30) × 1.2
    """
    return int((180 + pages * 30) * 1.2)


def get_scan_type_config(scan_type: ScanType, configured_pages: Optional[dict] = None) -> dict:
    """
    Get configuration based on scan type.

    QUICK: Fast scan, basic compliance checks
    STANDARD: Balanced scan, all DPDP sections
    DEEP: Comprehensive scan, full analysis with NLP

    If configured_pages is provided, uses those values for page counts.
    Otherwise falls back to defaults.
    """
    # Default page counts
    quick_pages = 20
    standard_pages = 75
    deep_pages = 200

    # Use configured values if provided
    if configured_pages:
        quick_pages = configured_pages.get("quick_pages", quick_pages)
        standard_pages = configured_pages.get("standard_pages", standard_pages)
        deep_pages = configured_pages.get("deep_pages", deep_pages)

    # All scan types run all detectors and capture screenshots
    # They only differ in page count
    configs = {
        ScanType.QUICK: {
            "max_pages": quick_pages,
            "timeout_seconds": calculate_timeout(quick_pages),
            "capture_screenshots": True,
            "detectors": ["all"],
            "enable_nlp": False,
            "description": f"Quick scan - {quick_pages} pages, all DPDP sections",
        },
        ScanType.STANDARD: {
            "max_pages": standard_pages,
            "timeout_seconds": calculate_timeout(standard_pages),
            "capture_screenshots": True,
            "detectors": ["all"],
            "enable_nlp": False,
            "description": f"Standard scan - {standard_pages} pages, all DPDP sections",
        },
        ScanType.DEEP: {
            "max_pages": deep_pages,
            "timeout_seconds": calculate_timeout(deep_pages),
            "capture_screenshots": True,
            "detectors": ["all"],
            "enable_nlp": False,
            "description": f"Deep scan - {deep_pages} pages, all DPDP sections",
        },
    }
    return configs.get(scan_type, configs[ScanType.STANDARD])


def get_detectors_for_scan_type(scan_type: ScanType):
    """
    Get the appropriate detectors based on scan type.

    All scan types run the same detectors - they only differ in page count.
    """
    from app.detectors import (
        PrivacyNoticeDetector,
        ConsentDetector,
        DarkPatternDetector,
        ChildrenDataDetector,
        DataPrincipalRightsDetector,
        DataRetentionDetector,
        DataBreachNotificationDetector,
        SignificantDataFiduciaryDetector,
    )

    # All scan types run all detectors - only page count differs
    return [
        PrivacyNoticeDetector(),      # Section 5 - Privacy Notice
        ConsentDetector(),            # Section 6 - Consent (includes withdrawal 6(6))
        DataRetentionDetector(),      # Section 8 - Data Retention
        ChildrenDataDetector(),       # Section 9 - Children's Data
        SignificantDataFiduciaryDetector(),  # Section 10 - SDF obligations
        DataPrincipalRightsDetector(),       # Sections 11-14 (includes grievance Section 13)
        DataBreachNotificationDetector(),    # Section 8(6) - Breach Notification
        DarkPatternDetector(),               # Section 18 - Dark Patterns
    ]


async def _run_web_scan_async(task, scan_id: str, application_id: str):
    """Async implementation of web scan with real-time WebSocket progress."""
    reporter = None
    scan = None

    async with async_session_maker() as db:
        try:
            # Get scan and application
            scan = await db.get(Scan, uuid.UUID(scan_id))
            application = await db.get(Application, uuid.UUID(application_id))

            if not scan or not application:
                raise ValueError("Scan or Application not found")

            # Create progress reporter for WebSocket updates
            reporter = await create_progress_reporter(scan_id)
            reporter.set_total_steps(100)
            reporter.start_timer()

            # Update scan status
            scan.status = ScanStatus.RUNNING
            scan.started_at = datetime.utcnow()
            await db.commit()

            # Get scan configuration from database
            configured_pages = await get_scan_configuration_from_db(db)

            # Get scan type configuration with configured page counts
            scan_type_config = get_scan_type_config(scan.scan_type, configured_pages)

            # Phase 1: Initialization (0-10%)
            update_task_progress(0, 100, "Initializing scanner...")
            await reporter.update(
                step=0,
                message=f"Initializing {scan.scan_type.value.upper()} scan: {scan_type_config['description']}"
            )

            # Import scanner components
            from app.scanners.web.crawler import WebCrawler
            from app.evidence.screenshot import ScreenshotCapture

            await reporter.update(step=5, message="Scanner initialized, starting crawl...")

            # Phase 2: Crawling (10-40%)
            # Use config_overrides if provided, otherwise use scan_type defaults
            max_pages = scan_type_config["max_pages"]
            if scan.scan_config:
                max_pages = scan.scan_config.get("max_pages", max_pages)

            # Handle localhost URLs for Docker environment
            scan_url = application.url
            if scan_url:
                # Convert localhost to host.docker.internal for Docker access
                scan_url = scan_url.replace("localhost", "host.docker.internal")
                scan_url = scan_url.replace("127.0.0.1", "host.docker.internal")

            # Debug logging for scan configuration
            print(f"[SCAN DEBUG] Original URL: {application.url}")
            print(f"[SCAN DEBUG] Docker URL: {scan_url}")
            print(f"[SCAN DEBUG] Max pages: {max_pages}")
            print(f"[SCAN DEBUG] Scan type: {scan.scan_type}")
            print(f"[SCAN DEBUG] Auth config present: {bool(application.auth_config)}")
            if application.auth_config:
                print(f"[SCAN DEBUG] Auth type: {application.auth_config.get('auth_type') or application.auth_config.get('type', 'none')}")
                print(f"[SCAN DEBUG] Login URL: {application.auth_config.get('login_url', 'not set')}")
                credentials = application.auth_config.get('credentials', {})
                print(f"[SCAN DEBUG] Username configured: {bool(credentials.get('username') or application.auth_config.get('username'))}")

            # Create a callback to update progress during crawling
            async def on_page_discovered(pages_found: int, current_url: str):
                # Update the scan record in database during crawl
                scan.pages_scanned = pages_found
                scan.total_pages = max_pages  # Estimated max
                scan.current_url = current_url  # Save current URL for display
                await db.commit()

                # Sync reporter's internal page count
                reporter._pages_scanned = pages_found
                reporter._total_pages = max_pages

                # Calculate progress (crawl phase is 10-40%)
                crawl_progress = 10 + int((pages_found / max_pages) * 30)
                await reporter.update(
                    step=min(crawl_progress, 39),  # Cap at 39 to leave room for Phase 3
                    message=f"Crawling: {pages_found}/{max_pages} pages discovered",
                    current_url=current_url,
                )

            crawler = WebCrawler(
                base_url=scan_url,
                max_pages=max_pages,
                auth_config=application.auth_config,
                on_page_discovered=on_page_discovered,
            )

            # Set initial total pages estimate for progress display
            reporter.set_total_pages(max_pages)
            await reporter.update(step=10, message=f"Crawling website: {application.url} (max {max_pages} pages)")

            pages = await crawler.crawl()
            total_pages = len(pages)

            # Set total pages for progress tracking
            reporter.set_total_pages(total_pages)
            scan.total_pages = total_pages

            # Debug logging for crawl results
            print(f"[SCAN DEBUG] Crawl complete - Total pages found: {total_pages}")
            for i, pg in enumerate(pages[:10]):  # Log first 10 pages
                print(f"[SCAN DEBUG] Page {i+1}: {pg.url} - Title: {pg.title[:50] if pg.title else 'No title'}")
            if total_pages > 10:
                print(f"[SCAN DEBUG] ... and {total_pages - 10} more pages")

            await reporter.update(
                step=40,
                message=f"Crawl complete. Found {total_pages} pages.",
                increment_pages=total_pages
            )

            # Phase 3: Scanning pages (40-90%)
            screenshot_capture = ScreenshotCapture() if scan_type_config["capture_screenshots"] else None

            # Initialize detectors based on scan type
            detectors = get_detectors_for_scan_type(scan.scan_type)

            all_findings: List[Finding] = []
            findings_count = 0
            pages_scanned = 0

            for i, page in enumerate(pages):
                progress_percent = 40 + int((i / total_pages) * 50)
                current_url = page.url if hasattr(page, 'url') else str(page)

                await reporter.update(
                    step=progress_percent,
                    message=f"Scanning page {i+1}/{total_pages}",
                    current_url=current_url,
                )
                update_task_progress(progress_percent, 100, f"Scanning: {current_url}")

                # Run all detectors on the page
                for detector in detectors:
                    try:
                        findings = await detector.detect(page)
                        for finding_data in findings:
                            # Create finding record
                            finding = Finding(
                                scan_id=uuid.UUID(scan_id),
                                check_type=finding_data.check_type,
                                severity=finding_data.severity,
                                status=finding_data.status,
                                title=finding_data.title,
                                description=finding_data.description,
                                dpdp_section=finding_data.dpdp_section,
                                remediation=finding_data.remediation,
                                location=current_url,
                                element_selector=getattr(finding_data, 'element_selector', None),
                                extra_data=getattr(finding_data, 'extra_data', None),
                            )
                            db.add(finding)
                            all_findings.append(finding)
                            findings_count += 1

                            # Track severity count
                            severity_value = finding_data.severity.value if hasattr(finding_data.severity, 'value') else finding_data.severity
                            reporter.increment_severity(severity_value)

                            # Report finding via WebSocket
                            await reporter.report_finding({
                                "id": str(finding.id),
                                "title": finding_data.title,
                                "severity": severity_value,
                                "status": finding_data.status.value if hasattr(finding_data.status, 'value') else finding_data.status,
                                "dpdp_section": finding_data.dpdp_section,
                                "description": finding_data.description,
                                "remediation": finding_data.remediation,
                                "url": current_url,
                            })
                            await reporter.update(increment_findings=1)

                    except Exception as detector_error:
                        # Log but continue with other detectors
                        print(f"Detector {detector.__class__.__name__} error: {detector_error}")

                pages_scanned += 1
                scan.pages_scanned = pages_scanned
                scan.findings_count = findings_count
                scan.current_url = current_url  # Update current URL being scanned

                # Commit after each page so progress is visible in the frontend
                await db.commit()

            # Final commit (in case there were no pages)
            await db.commit()

            # Phase 4: Capture violation screenshots (90-95%)
            # For Critical, High, and Medium severity findings WHERE the element EXISTS on the page
            # Skip screenshots for "missing" findings (no element_selector means nothing to highlight)
            screenshot_findings = [
                f for f in all_findings
                if f.severity in [FindingSeverity.CRITICAL, FindingSeverity.HIGH, FindingSeverity.MEDIUM]
                and f.element_selector  # Only if element exists (not a "missing" finding)
            ]

            print(f"[SCAN] Phase 4: Screenshot capture - Total findings: {len(all_findings)}, Critical/High/Medium with element: {len(screenshot_findings)}")

            if screenshot_findings:
                await reporter.update(step=90, message=f"Capturing screenshots for {len(screenshot_findings)} violations...")
                update_task_progress(90, 100, f"Capturing screenshots for {len(screenshot_findings)} violations...")

                try:
                    from app.evidence.violation_screenshot import ViolationScreenshotService

                    screenshot_service = ViolationScreenshotService()
                    await screenshot_service.initialize()

                    # Prepare findings data for batch capture
                    findings_for_screenshot = [
                        {
                            "id": str(f.id),
                            "location": f.location,
                            "element_selector": f.element_selector,
                            "title": f.title,
                            "severity": f.severity,
                            "check_type": f.check_type.value if hasattr(f.check_type, 'value') else str(f.check_type),
                        }
                        for f in screenshot_findings
                        if f.location and not f.location.startswith("windows://")  # Only web pages
                    ]

                    print(f"[SCAN] Eligible for screenshot (web pages only): {len(findings_for_screenshot)}")
                    for fsdata in findings_for_screenshot:
                        print(f"[SCAN] Finding for screenshot: id={fsdata['id'][:8]}, type={fsdata['check_type']}, selector={fsdata['element_selector']}")

                    if findings_for_screenshot:
                        screenshot_results = await screenshot_service.capture_batch_screenshots(
                            scan_id=scan_id,
                            findings=findings_for_screenshot,
                            auth_config=application.auth_config,
                            max_concurrent=2,  # Limit concurrent captures
                        )

                        # Update findings with screenshot paths using direct database updates
                        # This is more reliable than modifying objects that were committed earlier
                        from sqlalchemy import update

                        updated_count = 0
                        for result in screenshot_results:
                            print(f"[SCAN] Screenshot result: finding={result.finding_id[:8]}, success={result.success}, path={result.storage_path}")
                            if result.success and result.storage_path:
                                try:
                                    # Use direct UPDATE statement to ensure the change is saved
                                    stmt = update(Finding).where(
                                        Finding.id == uuid.UUID(result.finding_id)
                                    ).values(screenshot_path=result.storage_path)
                                    await db.execute(stmt)
                                    updated_count += 1
                                    print(f"[SCAN] Updated finding {result.finding_id[:8]} with screenshot path: {result.storage_path}")

                                    # Also update the in-memory object for consistency
                                    for finding in all_findings:
                                        if str(finding.id) == result.finding_id:
                                            finding.screenshot_path = result.storage_path
                                            break
                                except Exception as update_error:
                                    print(f"[SCAN] Error updating finding {result.finding_id[:8]}: {update_error}")

                        await db.commit()
                        print(f"[SCAN] Screenshot phase complete: {sum(1 for r in screenshot_results if r.success)} captured, {updated_count} findings updated")
                    else:
                        print("[SCAN] No eligible findings for screenshot capture (all filtered out)")

                    await screenshot_service.close()

                except Exception as screenshot_error:
                    import traceback
                    print(f"[SCAN] Screenshot capture error (non-fatal): {screenshot_error}")
                    print(f"[SCAN] Traceback: {traceback.format_exc()}")
                    # Continue with scan completion even if screenshots fail
            else:
                print("[SCAN] No Critical/High findings - skipping screenshot capture")

            # Phase 5: Finalizing (95-100%)
            await reporter.update(step=95, message="Calculating compliance score...")
            update_task_progress(95, 100, "Calculating compliance score...")

            # Calculate severity counts
            critical_count = sum(1 for f in all_findings if f.severity == FindingSeverity.CRITICAL)
            high_count = sum(1 for f in all_findings if f.severity == FindingSeverity.HIGH)
            medium_count = sum(1 for f in all_findings if f.severity == FindingSeverity.MEDIUM)
            low_count = sum(1 for f in all_findings if f.severity == FindingSeverity.LOW)

            # Calculate DPDP compliance score using advanced section-based scoring
            from app.core.scoring import calculate_compliance_score
            score_result = calculate_compliance_score(
                findings=all_findings,
                pages_scanned=pages_scanned,
                return_detailed=True
            )
            overall_score = score_result.overall_score

            # Update scan with results
            scan.status = ScanStatus.COMPLETED
            scan.completed_at = datetime.utcnow()
            scan.overall_score = overall_score
            scan.critical_count = critical_count
            scan.high_count = high_count
            scan.medium_count = medium_count
            scan.low_count = low_count
            scan.findings_count = findings_count
            scan.pages_scanned = pages_scanned
            await db.commit()

            # Send completion notification
            await reporter.update(step=100, message="Scan completed successfully!")
            await reporter.complete(
                status="completed",
                summary={
                    "pages_scanned": pages_scanned,
                    "findings_count": findings_count,
                    "overall_score": overall_score,
                    "grade": score_result.grade,
                    "risk_level": score_result.risk_level,
                    "penalty_exposure": score_result.penalty_exposure,
                    "critical": critical_count,
                    "high": high_count,
                    "medium": medium_count,
                    "low": low_count,
                }
            )
            update_task_progress(100, 100, "Scan completed")

            return {
                "scan_id": scan_id,
                "status": "completed",
                "pages_scanned": pages_scanned,
                "findings_count": findings_count,
                "overall_score": overall_score,
            }

        except Exception as e:
            # Mark scan as failed
            if scan:
                scan.status = ScanStatus.FAILED
                scan.status_message = str(e)
                scan.completed_at = datetime.utcnow()
                await db.commit()

            # Send error via WebSocket
            if reporter:
                await reporter.error(str(e))

            raise

        finally:
            # Clean up reporter
            if reporter:
                await reporter.disconnect()


@celery_app.task(bind=True, name="app.workers.tasks.scan_tasks.run_windows_scan")
def run_windows_scan(self, scan_id: str, application_id: str):
    """
    Execute a Windows application compliance scan.

    This task:
    1. Launches the target Windows application
    2. Navigates through UI using pywinauto
    3. Captures screenshots with OpenCV
    4. Performs OCR using Tesseract
    5. Runs compliance detectors on extracted text
    6. Stores findings and evidence
    """
    try:
        return asyncio.get_event_loop().run_until_complete(
            _run_windows_scan_async(self, scan_id, application_id)
        )
    except Exception as e:
        # Handle timeout and other exceptions that escape the async handler
        error_message = str(e)
        if "SoftTimeLimitExceeded" in type(e).__name__ or "TimeLimitExceeded" in type(e).__name__:
            error_message = "Scan timed out. Try reducing the number of pages or using a Quick scan."

        # Update scan status synchronously
        try:
            import asyncio as aio
            loop = aio.new_event_loop()
            loop.run_until_complete(_mark_scan_failed(scan_id, error_message))
            loop.close()
        except Exception as update_error:
            print(f"[SCAN] Failed to update scan status: {update_error}")

        raise


async def _run_windows_scan_async(task, scan_id: str, application_id: str):
    """Async implementation of Windows scan with real-time WebSocket progress."""
    reporter = None
    scan = None

    async with async_session_maker() as db:
        try:
            # Get scan and application
            scan = await db.get(Scan, uuid.UUID(scan_id))
            application = await db.get(Application, uuid.UUID(application_id))

            if not scan or not application:
                raise ValueError("Scan or Application not found")

            # Create progress reporter for WebSocket updates
            reporter = await create_progress_reporter(scan_id)
            reporter.set_total_steps(100)
            reporter.start_timer()

            # Update scan status
            scan.status = ScanStatus.RUNNING
            scan.started_at = datetime.utcnow()
            await db.commit()

            # Get scan configuration from database
            configured_pages = await get_scan_configuration_from_db(db)

            # Get scan type configuration with configured page counts
            scan_type_config = get_scan_type_config(scan.scan_type, configured_pages)

            # Phase 1: Initialization (0-10%)
            update_task_progress(0, 100, "Launching Windows application...")
            await reporter.update(
                step=0,
                message=f"Initializing {scan.scan_type.value.upper()} scan: {scan_type_config['description']}"
            )

            # Import scanner components
            from app.scanners.windows.controller import WindowsController
            from app.scanners.windows.vision import WindowsVisionAnalyzer
            from app.scanners.windows.ocr_processor import OCRProcessor
            from app.evidence.screenshot import ScreenshotCapture

            await reporter.update(step=5, message="Scanner initialized...")

            # Phase 2: Launch application (10-20%)
            await reporter.update(step=10, message=f"Launching: {application.name}")

            controller = WindowsController(application.executable_path)
            await controller.launch()

            await reporter.update(step=20, message="Application launched, discovering windows...")

            # Phase 3: Enumerate windows (20-30%)
            windows = await controller.enumerate_windows()
            total_windows = len(windows)

            await reporter.update(
                step=30,
                message=f"Found {total_windows} windows to scan",
            )

            # Phase 4: Scanning windows (30-85%)
            vision_analyzer = WindowsVisionAnalyzer()
            ocr_processor = OCRProcessor()
            screenshot_capture = ScreenshotCapture()

            # Languages for OCR (English + Hindi as per requirements)
            ocr_languages = ["en", "hi"]

            all_findings: List[Finding] = []
            findings_count = 0
            windows_scanned = 0

            for i, window in enumerate(windows):
                progress_percent = 30 + int((i / total_windows) * 55)
                window_title = window.title if hasattr(window, 'title') else f"Window {i+1}"

                await reporter.update(
                    step=progress_percent,
                    message=f"Scanning window {i+1}/{total_windows}: {window_title}",
                    current_url=window_title,  # Using current_url field for window name
                )
                update_task_progress(progress_percent, 100, f"Scanning: {window_title}")

                try:
                    # Capture screenshot
                    window_handle = window.handle if hasattr(window, 'handle') else None
                    screenshot = await screenshot_capture.capture_windows_screen(window_handle)

                    # Perform OCR and vision analysis
                    vision_result = await vision_analyzer.analyze_screenshot(
                        screenshot.file_path,
                        languages=ocr_languages
                    )

                    # Create a page-like object for detectors
                    class WindowPage:
                        def __init__(self, title, text, elements, screenshot_path):
                            self.url = f"windows://{title}"
                            self.title = title
                            self.text_content = text
                            self.html = ""  # No HTML for Windows apps
                            self.dom_tree = None
                            self.ui_elements = elements
                            self.screenshot_path = screenshot_path

                    window_page = WindowPage(
                        title=window_title,
                        text=vision_result.ocr_result.full_text if vision_result.ocr_result else "",
                        elements=vision_result.ui_elements if vision_result else [],
                        screenshot_path=screenshot.file_path,
                    )

                    # Initialize detectors based on scan type
                    detectors = get_detectors_for_scan_type(scan.scan_type)

                    # Run detectors
                    for detector in detectors:
                        try:
                            # Some detectors may need adaptation for Windows context
                            findings = await detector.detect(window_page)
                            for finding_data in findings:
                                finding = Finding(
                                    scan_id=uuid.UUID(scan_id),
                                    check_type=finding_data.check_type,
                                    severity=finding_data.severity,
                                    status=finding_data.status,
                                    title=finding_data.title,
                                    description=finding_data.description,
                                    dpdp_section=finding_data.dpdp_section,
                                    remediation=finding_data.remediation,
                                    location=f"windows://{window_title}",
                                    element_selector=getattr(finding_data, 'element_selector', None),
                                    extra_data=getattr(finding_data, 'extra_data', None),
                                )
                                db.add(finding)
                                all_findings.append(finding)
                                findings_count += 1

                                await reporter.report_finding({
                                    "title": finding_data.title,
                                    "severity": finding_data.severity.value if hasattr(finding_data.severity, 'value') else finding_data.severity,
                                    "dpdp_section": finding_data.dpdp_section,
                                    "window": window_title,
                                })
                                await reporter.update(increment_findings=1)

                        except Exception as detector_error:
                            print(f"Detector {detector.__class__.__name__} error on window: {detector_error}")

                    # Check for dark patterns detected by vision analyzer
                    if vision_result and vision_result.dark_patterns:
                        for dp in vision_result.dark_patterns:
                            finding = Finding(
                                scan_id=uuid.UUID(scan_id),
                                check_type=CheckType.DARK_PATTERN_MISDIRECTION,
                                severity=FindingSeverity.HIGH,
                                status=FindingStatus.FAIL,
                                title=f"Dark Pattern Detected: {dp.get('type', 'Unknown')}",
                                description=dp.get('description', 'Dark pattern identified in UI'),
                                dpdp_section="Dark Patterns",
                                remediation="Remove or modify the dark pattern to ensure transparent user experience",
                                location=f"windows://{window_title}",
                            )
                            db.add(finding)
                            all_findings.append(finding)
                            findings_count += 1

                except Exception as window_error:
                    print(f"Error scanning window {window_title}: {window_error}")

                windows_scanned += 1
                scan.pages_scanned = windows_scanned  # Reusing pages_scanned for windows
                scan.findings_count = findings_count

            await db.commit()

            # Phase 5: Cleanup (85-90%)
            await reporter.update(step=85, message="Closing application...")
            await controller.close()

            # Phase 6: Finalizing (90-100%)
            await reporter.update(step=90, message="Calculating compliance score...")
            update_task_progress(90, 100, "Calculating compliance score...")

            # Calculate severity counts
            critical_count = sum(1 for f in all_findings if f.severity == FindingSeverity.CRITICAL)
            high_count = sum(1 for f in all_findings if f.severity == FindingSeverity.HIGH)
            medium_count = sum(1 for f in all_findings if f.severity == FindingSeverity.MEDIUM)
            low_count = sum(1 for f in all_findings if f.severity == FindingSeverity.LOW)

            # Calculate DPDP compliance score using advanced section-based scoring
            from app.core.scoring import calculate_compliance_score
            score_result = calculate_compliance_score(
                findings=all_findings,
                pages_scanned=windows_scanned,
                return_detailed=True
            )
            overall_score = score_result.overall_score

            # Update scan with results
            scan.status = ScanStatus.COMPLETED
            scan.completed_at = datetime.utcnow()
            scan.overall_score = overall_score
            scan.critical_count = critical_count
            scan.high_count = high_count
            scan.medium_count = medium_count
            scan.low_count = low_count
            scan.findings_count = findings_count
            scan.pages_scanned = windows_scanned
            await db.commit()

            # Send completion notification
            await reporter.update(step=100, message="Scan completed successfully!")
            await reporter.complete(
                status="completed",
                summary={
                    "windows_scanned": windows_scanned,
                    "findings_count": findings_count,
                    "overall_score": overall_score,
                    "grade": score_result.grade,
                    "risk_level": score_result.risk_level,
                    "penalty_exposure": score_result.penalty_exposure,
                    "critical": critical_count,
                    "high": high_count,
                    "medium": medium_count,
                    "low": low_count,
                }
            )
            update_task_progress(100, 100, "Scan completed")

            return {
                "scan_id": scan_id,
                "status": "completed",
                "windows_scanned": windows_scanned,
                "findings_count": findings_count,
                "overall_score": overall_score,
            }

        except Exception as e:
            # Mark scan as failed
            if scan:
                scan.status = ScanStatus.FAILED
                scan.status_message = str(e)
                scan.completed_at = datetime.utcnow()
                await db.commit()

            # Send error via WebSocket
            if reporter:
                await reporter.error(str(e))

            raise

        finally:
            # Clean up reporter
            if reporter:
                await reporter.disconnect()


@celery_app.task(bind=True, name="app.workers.tasks.scan_tasks.cancel_scan")
def cancel_scan(self, scan_id: str):
    """Cancel a running scan."""
    return asyncio.get_event_loop().run_until_complete(
        _cancel_scan_async(scan_id)
    )


async def _cancel_scan_async(scan_id: str):
    """Async implementation of scan cancellation."""
    async with async_session_maker() as db:
        scan = await db.get(Scan, uuid.UUID(scan_id))
        if scan and scan.status == ScanStatus.RUNNING:
            scan.status = ScanStatus.CANCELLED
            scan.completed_at = datetime.utcnow()
            await db.commit()
            return {"scan_id": scan_id, "status": "cancelled"}
        return {"scan_id": scan_id, "status": "not_running"}
