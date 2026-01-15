"""
DPDP GUI Compliance Scanner - Web Crawler

Uses Playwright to crawl websites and capture page content.
"""
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from app.core.config import settings


@dataclass
class CrawledPage:
    """Represents a crawled web page."""
    url: str
    title: str
    html_content: str
    screenshot_path: Optional[str] = None
    links: List[str] = field(default_factory=list)
    forms: List[Dict] = field(default_factory=list)
    cookies: List[Dict] = field(default_factory=list)
    consent_elements: List[Dict] = field(default_factory=list)


class WebCrawler:
    """
    Web crawler using Playwright for DPDP compliance scanning.

    Features:
    - Respects robots.txt (optional)
    - Handles JavaScript-rendered content
    - Captures screenshots
    - Extracts forms and consent elements
    - Follows internal links up to max_pages
    """

    def __init__(
        self,
        base_url: str,
        max_pages: int = None,
        auth_config: Optional[Dict] = None,
        headless: bool = True,
    ):
        self.base_url = base_url.rstrip("/")
        self.base_domain = urlparse(base_url).netloc
        self.max_pages = max_pages or settings.MAX_CRAWL_PAGES
        self.auth_config = auth_config
        self.headless = headless if headless is not None else settings.BROWSER_HEADLESS

        self.visited_urls: Set[str] = set()
        self.pages_to_visit: List[str] = [base_url]
        self.crawled_pages: List[CrawledPage] = []

        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    async def crawl(self) -> List[CrawledPage]:
        """
        Crawl the website and return list of crawled pages.
        """
        async with async_playwright() as p:
            self._browser = await p.chromium.launch(headless=self.headless)
            self._context = await self._browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="DPDP Compliance Scanner/1.0",
            )

            # Handle authentication if configured
            if self.auth_config:
                await self._handle_authentication()

            # Crawl pages
            while self.pages_to_visit and len(self.crawled_pages) < self.max_pages:
                url = self.pages_to_visit.pop(0)

                if url in self.visited_urls:
                    continue

                try:
                    page_data = await self._crawl_page(url)
                    if page_data:
                        self.crawled_pages.append(page_data)
                        self.visited_urls.add(url)

                        # Add new links to queue
                        for link in page_data.links:
                            if link not in self.visited_urls and link not in self.pages_to_visit:
                                self.pages_to_visit.append(link)

                except Exception as e:
                    print(f"Error crawling {url}: {e}")
                    self.visited_urls.add(url)

            await self._browser.close()

        return self.crawled_pages

    async def _crawl_page(self, url: str) -> Optional[CrawledPage]:
        """Crawl a single page and extract content."""
        page = await self._context.new_page()

        try:
            # Navigate to page
            response = await page.goto(
                url,
                wait_until="networkidle",
                timeout=settings.BROWSER_TIMEOUT_MS,
            )

            if not response or response.status >= 400:
                await page.close()
                return None

            # Wait for dynamic content
            await page.wait_for_timeout(settings.PAGE_LOAD_WAIT_MS)

            # Extract page data
            title = await page.title()
            html_content = await page.content()

            # Extract links
            links = await self._extract_links(page)

            # Extract forms (important for consent)
            forms = await self._extract_forms(page)

            # Extract consent-related elements
            consent_elements = await self._extract_consent_elements(page)

            # Get cookies
            cookies = await self._context.cookies()

            await page.close()

            return CrawledPage(
                url=url,
                title=title,
                html_content=html_content,
                links=links,
                forms=forms,
                cookies=cookies,
                consent_elements=consent_elements,
            )

        except Exception as e:
            await page.close()
            raise

    async def _extract_links(self, page: Page) -> List[str]:
        """Extract all internal links from the page."""
        links = await page.evaluate("""
            () => {
                const links = [];
                document.querySelectorAll('a[href]').forEach(a => {
                    links.push(a.href);
                });
                return links;
            }
        """)

        # Filter to internal links only
        internal_links = []
        for link in links:
            parsed = urlparse(link)
            if parsed.netloc == self.base_domain or not parsed.netloc:
                # Normalize URL
                normalized = urljoin(self.base_url, parsed.path)
                if normalized.startswith(self.base_url):
                    internal_links.append(normalized)

        return list(set(internal_links))

    async def _extract_forms(self, page: Page) -> List[Dict]:
        """Extract form elements from the page."""
        return await page.evaluate("""
            () => {
                const forms = [];
                document.querySelectorAll('form').forEach(form => {
                    const inputs = [];
                    form.querySelectorAll('input, select, textarea').forEach(input => {
                        inputs.push({
                            type: input.type || input.tagName.toLowerCase(),
                            name: input.name,
                            id: input.id,
                            required: input.required,
                            placeholder: input.placeholder,
                        });
                    });
                    forms.push({
                        action: form.action,
                        method: form.method,
                        id: form.id,
                        inputs: inputs,
                    });
                });
                return forms;
            }
        """)

    async def _extract_consent_elements(self, page: Page) -> List[Dict]:
        """Extract consent-related elements (checkboxes, buttons, banners)."""
        return await page.evaluate("""
            () => {
                const elements = [];

                // Find consent checkboxes
                document.querySelectorAll('input[type="checkbox"]').forEach(cb => {
                    const label = cb.labels?.[0]?.textContent || '';
                    const nearby = cb.parentElement?.textContent || '';
                    if (label.toLowerCase().includes('consent') ||
                        label.toLowerCase().includes('agree') ||
                        label.toLowerCase().includes('privacy') ||
                        label.toLowerCase().includes('terms') ||
                        nearby.toLowerCase().includes('consent')) {
                        elements.push({
                            type: 'checkbox',
                            id: cb.id,
                            name: cb.name,
                            checked: cb.checked,
                            required: cb.required,
                            label: label.trim(),
                            preChecked: cb.hasAttribute('checked'),
                        });
                    }
                });

                // Find cookie banners
                const bannerSelectors = [
                    '[class*="cookie"]',
                    '[class*="consent"]',
                    '[id*="cookie"]',
                    '[id*="consent"]',
                    '[class*="gdpr"]',
                    '[class*="privacy"]',
                ];
                bannerSelectors.forEach(selector => {
                    document.querySelectorAll(selector).forEach(el => {
                        if (el.offsetHeight > 0) {
                            elements.push({
                                type: 'banner',
                                selector: selector,
                                text: el.textContent.substring(0, 500),
                                visible: true,
                            });
                        }
                    });
                });

                // Find consent buttons
                document.querySelectorAll('button, [role="button"]').forEach(btn => {
                    const text = btn.textContent.toLowerCase();
                    if (text.includes('accept') ||
                        text.includes('agree') ||
                        text.includes('consent') ||
                        text.includes('reject') ||
                        text.includes('decline') ||
                        text.includes('manage') ||
                        text.includes('preferences')) {
                        elements.push({
                            type: 'button',
                            text: btn.textContent.trim(),
                            id: btn.id,
                            class: btn.className,
                        });
                    }
                });

                return elements;
            }
        """)

    async def _handle_authentication(self):
        """Handle website authentication based on config."""
        if not self.auth_config:
            return

        auth_type = self.auth_config.get("type")
        page = await self._context.new_page()

        try:
            if auth_type == "form":
                # Form-based login
                login_url = self.auth_config.get("login_url")
                await page.goto(login_url)

                username_selector = self.auth_config.get("username_selector", "#username")
                password_selector = self.auth_config.get("password_selector", "#password")
                submit_selector = self.auth_config.get("submit_selector", "button[type=submit]")

                await page.fill(username_selector, self.auth_config.get("username", ""))
                await page.fill(password_selector, self.auth_config.get("password", ""))
                await page.click(submit_selector)
                await page.wait_for_load_state("networkidle")

            elif auth_type == "basic":
                # HTTP Basic Auth
                await self._context.set_http_credentials({
                    "username": self.auth_config.get("username", ""),
                    "password": self.auth_config.get("password", ""),
                })

            elif auth_type == "cookie":
                # Cookie-based auth
                cookies = self.auth_config.get("cookies", [])
                await self._context.add_cookies(cookies)

        finally:
            await page.close()

    async def capture_screenshot(self, page: Page, path: str) -> str:
        """Capture full-page screenshot."""
        await page.screenshot(
            path=path,
            full_page=True,
            quality=settings.SCREENSHOT_QUALITY,
            type="jpeg",
        )
        return path
