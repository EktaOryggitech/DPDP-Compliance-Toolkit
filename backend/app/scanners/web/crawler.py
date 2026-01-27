"""
DPDP GUI Compliance Scanner - Web Crawler

Uses Playwright to crawl websites and capture page content.
Supports Single Page Applications (SPAs) including Angular, React, Vue.

Features:
- Click-based navigation discovery for SPAs
- Angular/React/Vue framework detection and waiting
- Material UI / Bootstrap / PrimeNG component support
- Lazy loading and dynamic content handling
- Menu expansion and sidebar navigation
"""
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
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
    route_path: Optional[str] = None  # SPA route path


class WebCrawler:
    """
    Web crawler using Playwright for DPDP compliance scanning.

    Features:
    - Respects robots.txt (optional)
    - Handles JavaScript-rendered content (SPAs)
    - Click-based navigation for Angular/React/Vue apps
    - Captures screenshots
    - Extracts forms and consent elements
    - Follows internal links up to max_pages
    - Supports Material UI, Bootstrap, PrimeNG components
    """

    # Navigation element selectors for SPAs
    NAV_SELECTORS = [
        # Standard navigation
        'nav a', 'nav button', '.nav a', '.nav button',
        '[role="navigation"] a', '[role="navigation"] button',
        # Sidebar navigation
        '.sidebar a', '.sidebar button', '.sidenav a', '.sidenav button',
        'aside a', 'aside button', '[role="complementary"] a',
        # Menu items
        '.menu-item', '.menu a', '.menu button',
        '[role="menuitem"]', '[role="menuitemcheckbox"]',
        # Material Design (Angular Material)
        'mat-nav-list a', 'mat-nav-list button', 'mat-list-item',
        'mat-sidenav a', 'mat-sidenav button', 'mat-menu-item',
        '[mat-list-item]', '[matListItem]', 'a[mat-list-item]',
        'mat-tree-node', '[mat-menu-item]', 'button[mat-menu-item]',
        # PrimeNG
        'p-menuitem a', 'p-panelmenu a', 'p-tieredmenu a',
        '.p-menuitem-link', '.p-panelmenu-header',
        # Bootstrap
        '.nav-link', '.nav-item a', '.navbar-nav a',
        '.list-group-item', '.dropdown-item',
        # Generic list navigation
        'li a', 'li button', 'ul a',
    ]

    # Menu toggle selectors (for expanding collapsed menus)
    MENU_TOGGLE_SELECTORS = [
        # Hamburger menus
        '.hamburger', '.menu-toggle', '.navbar-toggler',
        '[aria-label*="menu"]', '[aria-label*="Menu"]',
        'button.menu', '.burger-menu',
        # Material Design toggles
        'mat-sidenav-container button', '[mat-icon-button]',
        '.mat-drawer-toggle', 'button[aria-label*="sidenav"]',
        # Angular Material specific
        '[matMenuTriggerFor]', '[mat-menu-trigger-for]',
        '.mat-menu-trigger', 'button.mat-icon-button',
        '.mat-mdc-icon-button', 'mat-icon.menu',
        # Sidebar toggles
        '.sidebar-toggle', '.sidenav-toggle', '.vertical-menu-btn',
        'button.nav-toggle', '.toggle-sidebar',
        # Expandable items
        '.expandable', '[aria-expanded="false"]',
        'mat-expansion-panel-header', '.p-panelmenu-header',
        # Vertical menus
        '.vertical-nav', '.vertical-menu button',
        '.mat-list-item', 'mat-nav-list button',
    ]

    def __init__(
        self,
        base_url: str,
        max_pages: int = None,
        auth_config: Optional[Dict] = None,
        headless: bool = True,
        spa_mode: bool = True,  # Enable SPA navigation by default
    ):
        self.base_url = base_url.rstrip("/")
        self.base_domain = urlparse(base_url).netloc
        self.max_pages = max_pages or settings.MAX_CRAWL_PAGES
        self.auth_config = auth_config
        self.headless = headless if headless is not None else settings.BROWSER_HEADLESS
        self.spa_mode = spa_mode

        self.visited_urls: Set[str] = set()
        self.visited_routes: Set[str] = set()  # Track SPA routes
        self.pages_to_visit: List[str] = [base_url]
        self.nav_elements_to_click: List[Dict] = []  # SPA navigation queue
        self.crawled_pages: List[CrawledPage] = []
        self._detected_framework: Optional[str] = None  # Angular, React, Vue, etc.

        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._main_page: Optional[Page] = None  # Persistent page for SPA navigation

    async def crawl(self) -> List[CrawledPage]:
        """
        Crawl the website and return list of crawled pages.
        Supports both traditional multi-page sites and SPAs.
        """
        print(f"[SPA Crawler] Starting crawl of {self.base_url}")
        print(f"[SPA Crawler] SPA mode: {self.spa_mode}, Max pages: {self.max_pages}")
        print(f"[SPA Crawler] Auth config: {bool(self.auth_config)}")

        async with async_playwright() as p:
            self._browser = await p.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-web-security",  # Disable CORS for API calls
                    "--disable-features=IsolateOrigins,site-per-process",  # Allow cross-origin
                ]
            )
            self._context = await self._browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="DPDP Compliance Scanner/1.0",
                ignore_https_errors=True,  # Accept self-signed certificates
            )

            # Handle authentication if configured
            auth_page = None
            if self.auth_config:
                print(f"[SPA Crawler] Handling authentication...")
                auth_page = await self._handle_authentication()
                print(f"[SPA Crawler] Authentication completed")

            # Use authenticated page as main page, or create new one
            if auth_page:
                self._main_page = auth_page
                print(f"[SPA Crawler] Using authenticated page, current URL: {self._main_page.url}")
                # If we're on a post-login page (not login page), use it as starting point
                if "login" not in self._main_page.url.lower() and "signin" not in self._main_page.url.lower():
                    print(f"[SPA Crawler] Already on authenticated page, no navigation needed")
                    await self._wait_for_spa_ready(self._main_page)
                else:
                    # Navigate to base URL (strip /login from URL if present)
                    base_url_clean = self.base_url.replace("/login", "").replace("/signin", "")
                    print(f"[SPA Crawler] Navigating to base URL: {base_url_clean}")
                    await self._main_page.goto(
                        base_url_clean,
                        wait_until="networkidle",
                        timeout=settings.BROWSER_TIMEOUT_MS,
                    )
            else:
                # Create main page for SPA navigation
                self._main_page = await self._context.new_page()

                # Navigate to base URL first
                print(f"[SPA Crawler] Navigating to base URL: {self.base_url}")
                await self._main_page.goto(
                    self.base_url,
                    wait_until="networkidle",
                    timeout=settings.BROWSER_TIMEOUT_MS,
                )

            print(f"[SPA Crawler] Page loaded, current URL: {self._main_page.url}")
            await self._wait_for_spa_ready(self._main_page)

            # Detect SPA framework
            self._detected_framework = await self._detect_framework(self._main_page)
            if self._detected_framework:
                print(f"Detected SPA framework: {self._detected_framework}")

            # If we're authenticated and on a dashboard page, capture it first
            current_url = self._main_page.url
            if "login" not in current_url.lower() and "signin" not in current_url.lower():
                print(f"[SPA Crawler] Capturing authenticated page: {current_url}")
                page_data = await self._extract_page_content(self._main_page, current_url)
                if page_data:
                    self.crawled_pages.append(page_data)
                    self.visited_urls.add(current_url)
                    route = self._extract_route(current_url)
                    if route:
                        self.visited_routes.add(route)
                    print(f"[SPA Crawler] Captured authenticated page: {current_url} (route: {route})")

                # Clear pages_to_visit of login URLs since we're authenticated
                self.pages_to_visit = [url for url in self.pages_to_visit
                                        if "login" not in url.lower() and "signin" not in url.lower()]

            # Phase 1: Crawl using traditional link extraction
            while self.pages_to_visit and len(self.crawled_pages) < self.max_pages:
                url = self.pages_to_visit.pop(0)

                if url in self.visited_urls:
                    continue

                try:
                    page_data = await self._crawl_page(url)
                    if page_data:
                        self.crawled_pages.append(page_data)
                        self.visited_urls.add(url)
                        route = self._extract_route(url)
                        if route:
                            self.visited_routes.add(route)

                        # Add new links to queue
                        for link in page_data.links:
                            if link not in self.visited_urls and link not in self.pages_to_visit:
                                self.pages_to_visit.append(link)

                except Exception as e:
                    print(f"Error crawling {url}: {e}")
                    self.visited_urls.add(url)

            # Phase 2: SPA Navigation - Click-based discovery
            if self.spa_mode and len(self.crawled_pages) < self.max_pages:
                print(f"[SPA Crawler] Starting SPA navigation discovery (found {len(self.crawled_pages)} pages so far)...")
                await self._crawl_spa_navigation()
            else:
                print(f"[SPA Crawler] Skipping SPA navigation: spa_mode={self.spa_mode}, pages={len(self.crawled_pages)}, max={self.max_pages}")

            await self._main_page.close()
            await self._browser.close()

        print(f"[SPA Crawler] Crawl complete: {len(self.crawled_pages)} pages discovered")
        print(f"[SPA Crawler] Visited routes: {self.visited_routes}")
        return self.crawled_pages

    async def _crawl_spa_navigation(self):
        """
        Crawl SPA by clicking navigation elements and discovering routes.
        This handles Angular, React, Vue apps with client-side routing.
        """
        try:
            # Check if we're on an authenticated page (not login)
            current_url = self._main_page.url
            if "login" not in current_url.lower() and "signin" not in current_url.lower():
                # We're already on an authenticated page, don't navigate away
                print(f"[SPA Crawler] Starting SPA nav from current page: {current_url}")
            else:
                # Navigate to base URL for SPA crawling (go to root if on login page)
                parsed = urlparse(self.base_url)
                path = parsed.path.lower()
                # Check if this is a login page
                if "login" in path or "signin" in path:
                    # Go to root URL instead of trying to strip login from path
                    spa_start_url = f"{parsed.scheme}://{parsed.netloc}/"
                else:
                    spa_start_url = self.base_url
                print(f"[SPA Crawler] Navigating to SPA start URL: {spa_start_url}")
                await self._main_page.goto(
                    spa_start_url,
                    wait_until="networkidle",
                    timeout=settings.BROWSER_TIMEOUT_MS,
                )
            await self._wait_for_spa_ready(self._main_page)

            # Try to expand any collapsed menus first
            await self._expand_menus(self._main_page)

            # Discover all navigation elements
            nav_elements = await self._discover_nav_elements(self._main_page)
            print(f"[SPA Crawler] Found {len(nav_elements)} navigation elements")
            for i, nav in enumerate(nav_elements[:10]):  # Log first 10
                print(f"[SPA Crawler]   Nav {i+1}: '{nav.get('text')}' ({nav.get('tag')})")

            # Click each navigation element and crawl
            for nav_info in nav_elements:
                if len(self.crawled_pages) >= self.max_pages:
                    break

                try:
                    await self._navigate_and_crawl(nav_info)
                except Exception as e:
                    print(f"Error navigating to {nav_info.get('text', 'unknown')}: {e}")

        except Exception as e:
            print(f"Error in SPA navigation: {e}")

    async def _navigate_and_crawl(self, nav_info: Dict):
        """Navigate to a route via clicking and crawl the content."""
        selector = nav_info.get("selector")
        text = nav_info.get("text", "")

        # Get current URL before clicking
        url_before = self._main_page.url
        route_before = self._extract_route(url_before)

        try:
            # Find and click the element
            print(f"[SPA Crawler] Attempting to click: '{text}' (selector: {selector[:60] if selector else 'None'})")
            element = self._main_page.locator(selector).first
            is_visible = await element.is_visible()
            if not is_visible:
                # Try expanding menus again - the sidebar might have collapsed
                print(f"[SPA Crawler]   Element not visible, trying to expand menus first...")
                await self._expand_menus(self._main_page)
                await self._main_page.wait_for_timeout(500)  # Wait for animation

                # Check visibility again
                is_visible = await element.is_visible()
                if not is_visible:
                    print(f"[SPA Crawler]   Element still not visible after expand, skipping: '{text}'")
                    return
                else:
                    print(f"[SPA Crawler]   Element now visible after expand")

            # Click and wait for navigation
            await element.click()
            print(f"[SPA Crawler]   Clicked '{text}', waiting for navigation...")
            await self._wait_for_spa_ready(self._main_page)

            # Check if route changed
            url_after = self._main_page.url
            route_after = self._extract_route(url_after)
            print(f"[SPA Crawler]   Route: {route_before} -> {route_after}")

            if route_after and route_after != route_before and route_after not in self.visited_routes:
                print(f"Discovered SPA route: {route_after} (via '{text}')")
                self.visited_routes.add(route_after)

                # Crawl this new route
                page_data = await self._extract_page_content(self._main_page, url_after)
                if page_data:
                    page_data.route_path = route_after
                    self.crawled_pages.append(page_data)
                    self.visited_urls.add(url_after)

                    # Recursively discover more navigation in this route
                    if len(self.crawled_pages) < self.max_pages:
                        await self._expand_menus(self._main_page)
                        sub_nav = await self._discover_nav_elements(self._main_page)
                        for sub_info in sub_nav[:10]:  # Limit recursion
                            if len(self.crawled_pages) >= self.max_pages:
                                break
                            try:
                                await self._navigate_and_crawl(sub_info)
                            except:
                                pass

        except Exception as e:
            # Element might have been removed or is not clickable
            pass

    async def _discover_nav_elements(self, page: Page) -> List[Dict]:
        """Discover all navigation elements on the page."""
        nav_elements = []
        seen_texts = set()

        for selector in self.NAV_SELECTORS:
            try:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    try:
                        text = await element.text_content()
                        text = text.strip() if text else ""

                        # Skip empty, very short, or already seen items
                        if not text or len(text) < 2 or text.lower() in seen_texts:
                            continue

                        # Skip common non-navigation text
                        skip_texts = ['login', 'logout', 'sign in', 'sign out', 'register',
                                     'close', 'cancel', 'submit', 'save', 'delete', 'search']
                        if text.lower() in skip_texts:
                            continue

                        is_visible = await element.is_visible()
                        if not is_visible:
                            continue

                        # Get a unique selector for this element
                        unique_selector = await self._get_unique_selector(page, element)

                        seen_texts.add(text.lower())
                        nav_elements.append({
                            "selector": unique_selector or selector,
                            "text": text[:50],  # Limit text length
                            "tag": await element.evaluate("el => el.tagName"),
                        })

                    except:
                        continue

            except:
                continue

        return nav_elements

    async def _get_unique_selector(self, page: Page, element) -> Optional[str]:
        """Generate a unique CSS selector for an element."""
        try:
            return await element.evaluate("""el => {
                // Try ID first
                if (el.id) return '#' + el.id;

                // Try unique class combination
                if (el.className) {
                    const classes = el.className.split(' ').filter(c => c).join('.');
                    if (classes) {
                        const selector = el.tagName.toLowerCase() + '.' + classes;
                        if (document.querySelectorAll(selector).length === 1) {
                            return selector;
                        }
                    }
                }

                // Try data attributes
                for (const attr of el.attributes) {
                    if (attr.name.startsWith('data-')) {
                        const selector = `[${attr.name}="${attr.value}"]`;
                        if (document.querySelectorAll(selector).length === 1) {
                            return selector;
                        }
                    }
                }

                // Try text content for buttons/links
                const text = el.textContent?.trim();
                if (text && text.length < 50) {
                    const tag = el.tagName.toLowerCase();
                    const selector = `${tag}:has-text("${text.substring(0, 30)}")`;
                    return selector;
                }

                return null;
            }""")
        except:
            return None

    async def _expand_menus(self, page: Page):
        """Try to expand collapsed menus, sidebars, and expandable sections."""
        expanded_count = 0
        for selector in self.MENU_TOGGLE_SELECTORS:
            try:
                toggles = await page.query_selector_all(selector)
                if toggles:
                    print(f"[SPA Crawler] Found {len(toggles)} elements matching toggle selector: {selector}")
                for toggle in toggles[:5]:  # Limit to prevent infinite expansion
                    try:
                        is_visible = await toggle.is_visible()
                        if is_visible:
                            # Get element text for logging
                            text = await toggle.text_content()
                            text = text.strip()[:30] if text else "(no text)"
                            print(f"[SPA Crawler] Clicking toggle: '{text}' ({selector})")
                            await toggle.click()
                            expanded_count += 1
                            await page.wait_for_timeout(500)  # Brief wait for animation
                    except Exception as e:
                        continue
            except:
                continue
        if expanded_count > 0:
            print(f"[SPA Crawler] Expanded {expanded_count} menu toggles")

    async def _detect_framework(self, page: Page) -> Optional[str]:
        """Detect the frontend framework being used."""
        return await page.evaluate("""() => {
            // Angular detection
            if (window.ng || document.querySelector('[ng-version]') ||
                document.querySelector('[_ngcontent]') || window.getAllAngularRootElements) {
                return 'Angular';
            }

            // React detection
            if (window.React || window.__REACT_DEVTOOLS_GLOBAL_HOOK__ ||
                document.querySelector('[data-reactroot]') ||
                document.querySelector('[data-reactid]')) {
                return 'React';
            }

            // Vue detection
            if (window.Vue || window.__VUE__ ||
                document.querySelector('[data-v-]') ||
                document.querySelector('.__vue-root')) {
                return 'Vue';
            }

            // Next.js detection
            if (window.__NEXT_DATA__ || document.querySelector('#__next')) {
                return 'Next.js';
            }

            // Nuxt detection
            if (window.__NUXT__ || document.querySelector('#__nuxt')) {
                return 'Nuxt';
            }

            return null;
        }""")

    async def _wait_for_spa_ready(self, page: Page, timeout: int = 10000):
        """Wait for SPA framework to be ready and stable."""
        try:
            # Wait for network idle first
            await page.wait_for_load_state("networkidle", timeout=timeout)

            # Framework-specific waiting
            if self._detected_framework == "Angular":
                await self._wait_for_angular(page, timeout)
            elif self._detected_framework in ["React", "Next.js"]:
                await self._wait_for_react(page, timeout)
            elif self._detected_framework in ["Vue", "Nuxt"]:
                await self._wait_for_vue(page, timeout)

            # Additional wait for any framework
            await page.wait_for_timeout(settings.PAGE_LOAD_WAIT_MS)

        except Exception as e:
            # Fallback to simple timeout
            await page.wait_for_timeout(settings.PAGE_LOAD_WAIT_MS)

    async def _wait_for_angular(self, page: Page, timeout: int = 10000):
        """Wait for Angular zone to stabilize."""
        try:
            await page.evaluate("""() => {
                return new Promise((resolve) => {
                    // Check if Angular is present
                    if (!window.ng && !window.getAllAngularRootElements) {
                        resolve();
                        return;
                    }

                    // Try to wait for zone stability
                    try {
                        const testability = window.getAllAngularTestabilities?.();
                        if (testability && testability.length > 0) {
                            testability[0].whenStable(() => resolve());
                        } else {
                            // Fallback - wait a bit for rendering
                            setTimeout(resolve, 1000);
                        }
                    } catch (e) {
                        setTimeout(resolve, 1000);
                    }

                    // Timeout after 5 seconds
                    setTimeout(resolve, 5000);
                });
            }""")
        except:
            await page.wait_for_timeout(2000)

    async def _wait_for_react(self, page: Page, timeout: int = 10000):
        """Wait for React to finish rendering."""
        try:
            await page.evaluate("""() => {
                return new Promise((resolve) => {
                    // Use requestIdleCallback if available
                    if (window.requestIdleCallback) {
                        requestIdleCallback(() => resolve(), { timeout: 3000 });
                    } else {
                        // Fallback to setTimeout
                        setTimeout(resolve, 1000);
                    }
                });
            }""")
        except:
            await page.wait_for_timeout(1000)

    async def _wait_for_vue(self, page: Page, timeout: int = 10000):
        """Wait for Vue to finish updating."""
        try:
            await page.evaluate("""() => {
                return new Promise((resolve) => {
                    if (window.Vue && window.Vue.nextTick) {
                        window.Vue.nextTick(resolve);
                    } else {
                        setTimeout(resolve, 1000);
                    }
                });
            }""")
        except:
            await page.wait_for_timeout(1000)

    def _extract_route(self, url: str) -> Optional[str]:
        """Extract the route path from a URL."""
        try:
            parsed = urlparse(url)
            # Include path and hash for SPA routes (Angular often uses hash routing)
            route = parsed.path
            if parsed.fragment:
                route += '#' + parsed.fragment
            return route or "/"
        except:
            return None

    async def _extract_page_content(self, page: Page, url: str) -> Optional[CrawledPage]:
        """Extract content from the current page state."""
        try:
            title = await page.title()
            html_content = await page.content()
            links = await self._extract_links(page)
            forms = await self._extract_forms(page)
            consent_elements = await self._extract_consent_elements(page)
            cookies = await self._context.cookies()

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
            print(f"Error extracting page content: {e}")
            return None

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
        """Handle website authentication based on config.
        Returns the authenticated page if login was successful, None otherwise.
        """
        if not self.auth_config:
            return None

        auth_type = self.auth_config.get("auth_type") or self.auth_config.get("type")

        # Skip if no auth or auth_type is 'none'
        if not auth_type or auth_type == "none":
            return None

        page = await self._context.new_page()
        login_successful = False

        try:
            if auth_type == "credentials" or auth_type == "form":
                # Form-based login
                login_url = self.auth_config.get("login_url")
                if not login_url:
                    print("Warning: No login_url provided for form authentication")
                    return

                # Handle localhost URLs for Docker
                login_url = login_url.replace("localhost", "host.docker.internal")
                login_url = login_url.replace("127.0.0.1", "host.docker.internal")

                await page.goto(login_url, wait_until="networkidle", timeout=30000)

                # Get credentials
                credentials = self.auth_config.get("credentials", {})
                username = credentials.get("username", "") if credentials else self.auth_config.get("username", "")
                password = credentials.get("password", "") if credentials else self.auth_config.get("password", "")

                # Get selectors with better defaults for Angular Material and other frameworks
                default_username_selectors = [
                    # Angular FormControl - most common for Angular apps
                    "input[formcontrolname='email']", "input[formcontrolname='username']",
                    "input[formcontrolname='user']", "input[formcontrolname='login']",
                    # Standard IDs
                    "#username", "#email", "#user", "#login",
                    # Name attributes
                    "input[name='username']", "input[name='email']", "input[name='user']",
                    # Type attributes
                    "input[type='email']",
                    # Material Design
                    "input[matinput][type='email']", "input[matinput][type='text']",
                    "mat-form-field input[type='email']", "mat-form-field input[type='text']",
                    # Placeholders
                    "input[placeholder*='email' i]", "input[placeholder*='user' i]",
                    # Autocomplete hints
                    "input[autocomplete='username']", "input[autocomplete='email']",
                    # Fallback: first text input that's not password (often username/email)
                    "input[type='text']:not([type='password'])",
                ]
                default_password_selectors = [
                    # Angular FormControl - most common for Angular apps
                    "input[formcontrolname='password']", "input[formcontrolname='pass']",
                    # Type attribute - universal fallback
                    "input[type='password']",
                    # Standard IDs
                    "#password", "#pass", "#pwd",
                    # Name attributes
                    "input[name='password']", "input[name='pass']",
                    # Material Design
                    "input[matinput][type='password']",
                    "mat-form-field input[type='password']",
                ]
                default_submit_selectors = [
                    "button[type='submit']", "input[type='submit']",
                    "button[mat-raised-button]", "button[mat-flat-button]",
                    "button[color='primary']", "button.mat-primary",
                    "button:has-text('Login')", "button:has-text('Sign in')",
                    "button:has-text('Submit')", "button:has-text('Log in')",
                ]

                username_selector = self.auth_config.get("username_field") or self.auth_config.get("username_selector", ", ".join(default_username_selectors))
                password_selector = self.auth_config.get("password_field") or self.auth_config.get("password_selector", ", ".join(default_password_selectors))
                submit_selector = self.auth_config.get("submit_selector", ", ".join(default_submit_selectors))

                print(f"[SPA Crawler] Attempting login at: {login_url}")
                print(f"[SPA Crawler] Username selectors to try: {len(default_username_selectors)}")

                # Log credentials (partially masked for security)
                masked_user = username[:3] + "***" if len(username) > 3 else "***"
                masked_pass = "*" * len(password) if password else "(empty)"
                print(f"[SPA Crawler] Credentials: user={masked_user}, pass={masked_pass} ({len(password)} chars)")

                # Set up console and network error logging
                console_errors = []
                network_errors = []

                async def handle_console(msg):
                    if msg.type == "error":
                        console_errors.append(msg.text)
                        print(f"[SPA Crawler] CONSOLE ERROR: {msg.text[:200]}")

                async def handle_request_failed(request):
                    network_errors.append(f"{request.method} {request.url} - {request.failure}")
                    print(f"[SPA Crawler] NETWORK FAILED: {request.method} {request.url[:100]}")

                page.on("console", handle_console)
                page.on("requestfailed", handle_request_failed)

                # Intercept requests to localhost and redirect to host.docker.internal
                # This is needed because Angular app makes API calls to localhost which won't work inside Docker
                async def handle_route(route):
                    request = route.request
                    url = request.url
                    # Replace localhost with host.docker.internal for API calls
                    if "localhost" in url or "127.0.0.1" in url:
                        new_url = url.replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal")
                        print(f"[SPA Crawler] Redirecting: {url[:80]} -> {new_url[:80]}")
                        try:
                            await route.continue_(url=new_url)
                        except Exception as e:
                            print(f"[SPA Crawler] Route redirect failed: {e}")
                            await route.continue_()
                    else:
                        await route.continue_()

                await page.route("**/*", handle_route)
                print(f"[SPA Crawler] Request interception enabled - redirecting localhost to host.docker.internal")

                # Wait for Angular to render the form
                await page.wait_for_timeout(2000)  # Give Angular time to render

                # Try to find and fill username field
                username_filled = False
                try:
                    # First, try to find any text input that's not password
                    try:
                        # Wait for any input to appear
                        await page.wait_for_selector("input", timeout=5000)
                    except:
                        pass

                    # Try each selector until one works
                    for selector in username_selector.split(","):
                        selector = selector.strip()
                        try:
                            element = page.locator(selector).first
                            if await element.count() > 0 and await element.is_visible():
                                await element.fill(username)
                                print(f"[SPA Crawler] Filled username using selector: {selector}")
                                username_filled = True
                                break
                        except Exception as sel_err:
                            continue
                except Exception as e:
                    print(f"[SPA Crawler] Could not fill username: {e}")

                if not username_filled:
                    print(f"[SPA Crawler] WARNING: Failed to fill username field with CSS selectors. Trying JS fallback...")
                    # Try to get page HTML to debug
                    try:
                        inputs = await page.query_selector_all("input")
                        print(f"[SPA Crawler] Found {len(inputs)} input fields on login page:")
                        for inp in inputs[:5]:
                            inp_type = await inp.get_attribute("type")
                            inp_name = await inp.get_attribute("name")
                            inp_id = await inp.get_attribute("id")
                            inp_fc = await inp.get_attribute("formcontrolname")
                            print(f"[SPA Crawler]   input: type={inp_type}, name={inp_name}, id={inp_id}, formcontrolname={inp_fc}")

                            # Try to fill the first non-password input directly
                            if not username_filled and inp_type != "password":
                                try:
                                    await inp.fill(username)
                                    print(f"[SPA Crawler] Filled username via direct element (type={inp_type}, formcontrolname={inp_fc})")
                                    username_filled = True
                                except Exception as fill_err:
                                    print(f"[SPA Crawler] Direct fill failed: {fill_err}")
                    except Exception as e:
                        print(f"[SPA Crawler] Debug failed: {e}")

                # Try to find and fill password field
                password_filled = False
                try:
                    for selector in password_selector.split(","):
                        selector = selector.strip()
                        try:
                            element = page.locator(selector).first
                            if await element.count() > 0 and await element.is_visible():
                                await element.fill(password)
                                print(f"[SPA Crawler] Filled password using selector: {selector}")
                                password_filled = True
                                break
                        except:
                            continue
                except Exception as e:
                    print(f"[SPA Crawler] Could not fill password: {e}")

                if not password_filled:
                    print(f"[SPA Crawler] WARNING: Failed to fill password field!")

                # After filling password, also try pressing Enter (some forms need this)
                if password_filled:
                    try:
                        await page.keyboard.press("Enter")
                        print(f"[SPA Crawler] Pressed Enter key after password")
                        await page.wait_for_timeout(1000)  # Wait briefly for Enter to trigger submit
                    except Exception as e:
                        print(f"[SPA Crawler] Enter key press failed: {e}")

                # Try to click submit button
                submit_clicked = False
                try:
                    for selector in submit_selector.split(","):
                        selector = selector.strip()
                        try:
                            element = page.locator(selector).first
                            if await element.count() > 0 and await element.is_visible():
                                await element.click()
                                print(f"[SPA Crawler] Clicked submit using selector: {selector}")
                                submit_clicked = True
                                break
                        except:
                            continue
                except Exception as e:
                    print(f"[SPA Crawler] Could not click submit: {e}")

                if not submit_clicked:
                    print(f"[SPA Crawler] WARNING: Failed to click submit button!")

                # Wait for navigation/login to complete
                try:
                    # Wait for URL to change (successful login should redirect)
                    await page.wait_for_url(lambda url: "login" not in url.lower(), timeout=10000)
                    print(f"[SPA Crawler] Login successful - redirected to: {page.url}")
                    login_successful = True
                except:
                    # URL didn't change, wait for network idle and check
                    await page.wait_for_load_state("networkidle", timeout=10000)
                    await page.wait_for_timeout(3000)  # Extra wait for Angular
                    print(f"[SPA Crawler] Authentication completed, current URL: {page.url}")

                # Check if we have cookies (indicates successful login)
                cookies = await self._context.cookies()
                print(f"[SPA Crawler] Cookies after login: {len(cookies)} cookies")
                for cookie in cookies[:5]:  # Log first 5 cookies
                    print(f"[SPA Crawler]   Cookie: {cookie.get('name')} = {cookie.get('value', '')[:20]}...")

                # Check if we're not on login page anymore (successful login)
                if "login" not in page.url.lower() and "signin" not in page.url.lower():
                    login_successful = True

                # Check if we're still on login page (might indicate login failure)
                if not login_successful:
                    print(f"[SPA Crawler] WARNING: Still on login page after auth attempt!")
                    # Try to get any error messages
                    error_selectors = ['.error', '.alert-danger', '.error-message', '[role="alert"]', '.mat-error',
                                       '.invalid-feedback', '.ng-invalid', 'mat-error', '[class*="error"]',
                                       'snack-bar-container', '.mat-snack-bar-container', '.toast-error']
                    for selector in error_selectors:
                        try:
                            error_els = await page.query_selector_all(selector)
                            for error_el in error_els:
                                error_text = await error_el.text_content()
                                if error_text and error_text.strip():
                                    print(f"[SPA Crawler] Error found ({selector}): {error_text.strip()[:100]}")
                        except:
                            pass

                    # Also try to find any visible text that might indicate error
                    try:
                        page_text = await page.evaluate("""() => {
                            const body = document.body.innerText.toLowerCase();
                            const errorKeywords = ['invalid', 'incorrect', 'wrong', 'failed', 'error', 'unauthorized'];
                            for (const kw of errorKeywords) {
                                if (body.includes(kw)) {
                                    // Find the sentence containing the keyword
                                    const idx = body.indexOf(kw);
                                    return body.substring(Math.max(0, idx - 50), Math.min(body.length, idx + 100));
                                }
                            }
                            return null;
                        }""")
                        if page_text:
                            print(f"[SPA Crawler] Page text contains error indicators: ...{page_text}...")
                    except:
                        pass

                    # Summary of errors captured
                    if console_errors:
                        print(f"[SPA Crawler] Total console errors during login: {len(console_errors)}")
                    if network_errors:
                        print(f"[SPA Crawler] Total network failures during login: {len(network_errors)}")
                        for err in network_errors[:5]:
                            print(f"[SPA Crawler]   Network error: {err[:150]}")

            elif auth_type == "basic":
                # HTTP Basic Auth
                credentials = self.auth_config.get("credentials", {})
                username = credentials.get("username", "") if credentials else self.auth_config.get("username", "")
                password = credentials.get("password", "") if credentials else self.auth_config.get("password", "")

                await self._context.set_http_credentials({
                    "username": username,
                    "password": password,
                })

            elif auth_type == "cookie" or auth_type == "session":
                # Cookie-based auth
                cookies = self.auth_config.get("session_cookies") or self.auth_config.get("cookies", [])
                if cookies:
                    await self._context.add_cookies(cookies)

        except Exception as e:
            print(f"Authentication error: {e}")

        # Return the page if login was successful, otherwise close it
        if login_successful:
            print(f"[SPA Crawler] Keeping authenticated page for crawling")
            return page
        else:
            await page.close()
            return None

    async def capture_screenshot(self, page: Page, path: str) -> str:
        """Capture full-page screenshot."""
        await page.screenshot(
            path=path,
            full_page=True,
            quality=settings.SCREENSHOT_QUALITY,
            type="jpeg",
        )
        return path
