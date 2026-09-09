"""Abstract base crawler - the modular architecture core.

Every province adapter subclasses BaseCrawler and implements two methods:
    fetch_list_page(page)  -> list[ListItem]
    fetch_detail(item)     -> LetterRecord

The base class supplies HTTP/Playwright helpers, retry logic,
structure-change detection, and the crawl() orchestration loop.
"""
from __future__ import annotations

import re
import time
from abc import ABC, abstractmethod
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from .models import CrawlResult, CrawlStatus, ListItem, LetterRecord
from .retry import retry


class BaseCrawler(ABC):
    """Base class for all province crawlers."""

    max_pages: int = 5
    page_delay: float = 1.5

    def __init__(self, province_config: dict, settings: dict, logger=None):
        self.province: str = province_config["name"]
        self.province_id: str = province_config["id"]
        self.base_url: str = province_config["url"]
        self.crawler_type: str = province_config.get("crawler_type", "http")
        self.settings: dict = settings
        self.crawl_cfg: dict = settings.get("crawl", {})
        self.logger = logger

        self.max_pages = self.crawl_cfg.get("max_pages", self.max_pages)
        self.page_delay = self.crawl_cfg.get("page_delay", self.page_delay)

        self._http_client: Optional[httpx.Client] = None
        self._playwright = None
        self._browser = None
        self._page = None

    @abstractmethod
    def fetch_list_page(self, page: int) -> list[ListItem]:
        """Fetch one page of the letter list. Return [] when no more pages."""

    @abstractmethod
    def fetch_detail(self, item: ListItem) -> LetterRecord:
        """Fetch the detail page, return a full LetterRecord."""

    def crawl(self) -> CrawlResult:
        """Main entry: paginate list, fetch details, return CrawlResult."""
        result = CrawlResult(
            province=self.province,
            province_id=self.province_id,
        )
        start = time.time()
        all_items: list[ListItem] = []
        detail_errors = 0

        try:
            for page in range(1, self.max_pages + 1):
                self.logger.info(f"[{self.province}] Fetching list page {page}")
                items = self._fetch_list_with_retry(page)

                if not items:
                    self.logger.info(
                        f"[{self.province}] Page {page} returned 0 items, stopping"
                    )
                    break

                if page == 1:
                    min_items = self.crawl_cfg.get("min_list_items", 1)
                    if len(items) < min_items:
                        result.structure_alert = True
                        result.structure_alert_message = (
                            f"Page 1 returned only {len(items)} items "
                            f"(expected >= {min_items}), possible site change"
                        )
                        self.logger.warning(
                            f"[{self.province}] {result.structure_alert_message}"
                        )

                all_items.extend(items)
                if page < self.max_pages:
                    time.sleep(self.page_delay)

            result.total_found = len(all_items)
            self.logger.info(
                f"[{self.province}] Found {len(all_items)} items, fetching details..."
            )

            for item in all_items:
                try:
                    record = self._fetch_detail_with_retry(item)
                    result.records.append(record)
                except Exception as exc:
                    detail_errors += 1
                    self.logger.warning(
                        f"[{self.province}] Detail fetch failed for "
                        f"'{item.title}': {exc}"
                    )

        except Exception as exc:
            result.status = CrawlStatus.FAILED
            result.error_message = str(exc)
            self.logger.error(f"[{self.province}] Crawl failed: {exc}", exc_info=True)
        finally:
            result.duration_seconds = round(time.time() - start, 2)
            self.close()

        if result.status != CrawlStatus.FAILED:
            if detail_errors > 0 and detail_errors < len(all_items):
                result.status = CrawlStatus.PARTIAL
            elif len(result.records) == 0 and len(all_items) == 0:
                result.status = CrawlStatus.NO_NEW

        self.logger.info(
            f"[{self.province}] Crawl complete: status={result.status.value}, "
            f"records={len(result.records)}, errors={detail_errors}, "
            f"duration={result.duration_seconds}s"
        )
        return result

    def _fetch_list_with_retry(self, page: int) -> list[ListItem]:
        max_retries = self.crawl_cfg.get("http_retries", 3)
        backoff = self.crawl_cfg.get("retry_backoff", 2)
        return retry(
            max_retries=max_retries, backoff=backoff, logger=self.logger
        )(self.fetch_list_page)(page)

    def _fetch_detail_with_retry(self, item: ListItem) -> LetterRecord:
        max_retries = self.crawl_cfg.get("http_retries", 3)
        backoff = self.crawl_cfg.get("retry_backoff", 2)
        return retry(
            max_retries=max_retries, backoff=backoff, logger=self.logger
        )(self.fetch_detail)(item)

    @property
    def http_client(self) -> httpx.Client:
        """Lazy-initialized HTTP client with connection pooling."""
        if self._http_client is None:
            timeout = self.crawl_cfg.get("timeout", 30)
            ua = self.crawl_cfg.get(
                "user_agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
            )
            self._http_client = httpx.Client(
                headers={"User-Agent": ua},
                timeout=timeout,
                follow_redirects=True,
                verify=False,
            )
        return self._http_client

    def http_get(self, url: str, params: dict = None, headers: dict = None) -> str:
        """HTTP GET, return response text with encoding detection."""
        resp = self.http_client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        encoding = resp.charset_encoding
        if not encoding or encoding.lower() == "iso-8859-1":
            for enc in ("utf-8", "gbk", "gb2312"):
                try:
                    return resp.content.decode(enc)
                except (UnicodeDecodeError, LookupError):
                    continue
        return resp.text

    def http_get_json(self, url: str, params: dict = None, headers: dict = None) -> dict:
        """HTTP GET, return parsed JSON."""
        resp = self.http_client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        return resp.json()

    def http_post(self, url: str, data: dict = None, headers: dict = None) -> str:
        """HTTP POST (form data), return response text."""
        resp = self.http_client.post(url, data=data, headers=headers)
        resp.raise_for_status()
        encoding = resp.charset_encoding
        if not encoding or encoding.lower() == "iso-8859-1":
            for enc in ("utf-8", "gbk", "gb2312"):
                try:
                    return resp.content.decode(enc)
                except (UnicodeDecodeError, LookupError):
                    continue
        return resp.text

    def http_post_json(self, url: str, json_data: dict = None, headers: dict = None) -> dict:
        """HTTP POST (JSON body), return parsed JSON."""
        resp = self.http_client.post(url, json=json_data, headers=headers)
        resp.raise_for_status()
        return resp.json()

    def playwright_fetch(
        self, url: str, wait_for: str = None, wait_timeout: int = 10000
    ) -> str:
        """Render page with Playwright, return HTML."""
        if self._page is None:
            from playwright.sync_api import sync_playwright

            self._playwright = sync_playwright().start()
            headless = self.crawl_cfg.get("playwright_headless", True)
            self._browser = self._playwright.chromium.launch(headless=headless)
            self._page = self._browser.new_page()
            ua = self.crawl_cfg.get("user_agent")
            if ua:
                self._page.set_extra_http_headers({"User-Agent": ua})

        self.logger.info(f"[{self.province}] Playwright navigating to {url}")
        self._page.goto(url, wait_until="domcontentloaded")
        if wait_for:
            self._page.wait_for_selector(wait_for, timeout=wait_timeout)
        else:
            self._page.wait_for_load_state("networkidle")
        return self._page.content()

    def playwright_click_and_wait(
        self, selector: str, wait_for: str = None, wait_timeout: int = 10000
    ) -> str:
        """Click an element and return the updated page HTML."""
        if self._page is None:
            raise RuntimeError("Playwright page not initialized")
        self._page.click(selector)
        if wait_for:
            self._page.wait_for_selector(wait_for, timeout=wait_timeout)
        else:
            self._page.wait_for_load_state("networkidle")
        return self._page.content()

    @staticmethod
    def parse_html(html: str) -> BeautifulSoup:
        """Parse HTML string with BeautifulSoup (lxml parser)."""
        return BeautifulSoup(html, "lxml")

    @staticmethod
    def clean_text(text: str) -> str:
        """Normalize whitespace in extracted text."""
        if not text:
            return ""
        return re.sub(r"\s+", " ", text).strip()

    def join_url(self, url: str) -> str:
        """Resolve a possibly-relative URL against the base URL."""
        if url.startswith(("http://", "https://")):
            return url
        return urljoin(self.base_url, url)

    @staticmethod
    def extract_id_from_url(url: str, pattern: str = None) -> str:
        """Extract original_id from a URL via regex or last path segment."""
        if pattern:
            m = re.search(pattern, url)
            if m:
                return m.group(1)
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        last = path.rsplit("/", 1)[-1] if path else ""
        for ext in (".html", ".htm", ".shtml", ".aspx", ".do", ".jsp"):
            if last.lower().endswith(ext):
                last = last[: -len(ext)]
        return last or url

    def close(self) -> None:
        """Release HTTP client and Playwright resources."""
        if self._http_client:
            self._http_client.close()
            self._http_client = None
        if self._page:
            self._page.close()
            self._page = None
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
