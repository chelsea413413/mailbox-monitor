"""Abstract base crawler - the modular architecture core."""
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

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
}


class BaseCrawler(ABC):
    """Base class for all province crawlers."""

    max_pages: int = 5
    page_delay: float = 1.5

    def __init__(self, province_config: dict, settings: dict, logger=None):
        self.province = province_config["name"]
        self.province_id = province_config["id"]
        self.base_url = province_config["url"]
        self.crawler_type = province_config.get("crawler_type", "http")
        self.settings = settings
        self.crawl_cfg = settings.get("crawl", {})
        self.logger = logger
        self.max_pages = self.crawl_cfg.get("max_pages", self.max_pages)
        self.page_delay = self.crawl_cfg.get("page_delay", self.page_delay)
        self._http_client = None
        self._playwright = None
        self._browser = None
        self._page = None

    @abstractmethod
    def fetch_list_page(self, page: int) -> list:
        """Fetch one page of the letter list."""

    @abstractmethod
    def fetch_detail(self, item) -> LetterRecord:
        """Fetch the detail page, return a full LetterRecord."""

    def crawl(self) -> CrawlResult:
        result = CrawlResult(province=self.province, province_id=self.province_id)
        start = time.time()
        all_items = []
        detail_errors = 0
        try:
            for page in range(1, self.max_pages + 1):
                self.logger.info(f"[{self.province}] Fetching list page {page}")
                items = self._fetch_list_with_retry(page)
                if not items:
                    self.logger.info(f"[{self.province}] Page {page} returned 0 items, stopping")
                    break
                if page == 1:
                    min_items = self.crawl_cfg.get("min_list_items", 1)
                    if len(items) < min_items:
                        result.structure_alert = True
                        result.structure_alert_message = (
                            f"Page 1 returned only {len(items)} items, possible site change"
                        )
                        self.logger.warning(f"[{self.province}] {result.structure_alert_message}")
                all_items.extend(items)
                if page < self.max_pages:
                    time.sleep(self.page_delay)
            result.total_found = len(all_items)
            self.logger.info(f"[{self.province}] Found {len(all_items)} items, fetching details...")
            for item in all_items:
                try:
                    record = self._fetch_detail_with_retry(item)
                    result.records.append(record)
                except Exception as exc:
                    detail_errors += 1
                    self.logger.warning(f"[{self.province}] Detail fetch failed for '{item.title}': {exc}")
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

    def _fetch_list_with_retry(self, page: int) -> list:
        max_retries = self.crawl_cfg.get("http_retries", 3)
        backoff = self.crawl_cfg.get("retry_backoff", 2)
        return retry(max_retries=max_retries, backoff=backoff, logger=self.logger)(self.fetch_list_page)(page)

    def _fetch_detail_with_retry(self, item) -> LetterRecord:
        max_retries = self.crawl_cfg.get("http_retries", 3)
        backoff = self.crawl_cfg.get("retry_backoff", 2)
        return retry(max_retries=max_retries, backoff=backoff, logger=self.logger)(self.fetch_detail)(item)

    @property
    def http_client(self) -> httpx.Client:
        """HTTP client with IPv4 forcing and browser headers.

        Forces IPv4 (local_address='0.0.0.0') because GitHub Actions runners
        prefer IPv6, which Chinese gov sites do not support.
        """
        if self._http_client is None:
            timeout = self.crawl_cfg.get("timeout", 30)
            headers = dict(BROWSER_HEADERS)
            ua = self.crawl_cfg.get("user_agent")
            if ua:
                headers["User-Agent"] = ua
            transport = httpx.HTTPTransport(local_address="0.0.0.0", verify=False)
            self._http_client = httpx.Client(
                headers=headers, timeout=timeout, follow_redirects=True,
                verify=False, transport=transport,
            )
        return self._http_client

    def http_get(self, url: str, params: dict = None, headers: dict = None) -> str:
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
        resp = self.http_client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        return resp.json()

    def http_post(self, url: str, data: dict = None, headers: dict = None) -> str:
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
        resp = self.http_client.post(url, json=json_data, headers=headers)
        resp.raise_for_status()
        return resp.json()

    def playwright_fetch(self, url: str, wait_for: str = None, wait_timeout: int = 15000) -> str:
        """Render page with Playwright, return HTML."""
        self._init_playwright()
        self.logger.info(f"[{self.province}] Playwright navigating to {url}")
        self._page.goto(url, wait_until="commit", timeout=60000)
        if wait_for:
            try:
                self._page.wait_for_selector(wait_for, timeout=wait_timeout)
            except Exception as e:
                self.logger.warning(
                    f"[{self.province}] wait_for_selector timed out, "
                    f"continuing with available HTML: {e}"
                )
        else:
            self._page.wait_for_timeout(3000)
        return self._page.content()

    def _init_playwright(self):
        """Lazily start Playwright browser if not already running."""
        if self._page is not None:
            return
        from playwright.sync_api import sync_playwright
        self._playwright = sync_playwright().start()
        headless = self.crawl_cfg.get("playwright_headless", True)
        ua = self.crawl_cfg.get("user_agent", BROWSER_HEADERS["User-Agent"])
        self._browser = self._playwright.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )
        context = self._browser.new_context(
            user_agent=ua, locale="zh-CN",
            extra_http_headers={"Accept-Language": "zh-CN,zh;q=0.9"},
        )
        self._page = context.new_page()

    def playwright_get_json(self, url: str, params: dict = None, headers: dict = None) -> dict:
        """Fetch JSON by navigating the real browser to the API URL."""
        import json as _json
        from urllib.parse import urlencode
        self._init_playwright()
        full_url = f"{url}?{urlencode(params)}" if params else url
        self.logger.info(f"[{self.province}] Playwright JSON fetch: {full_url}")
        if headers:
            self._page.set_extra_http_headers(headers)
        response = self._page.goto(full_url, wait_until="commit", timeout=60000)
        try:
            self._page.wait_for_load_state("domcontentloaded", timeout=10000)
        except Exception:
            pass
        if response is not None:
            text = response.text()
        else:
            text = self._page.evaluate("() => document.body.innerText")
        if headers:
            self._page.set_extra_http_headers({})
        return _json.loads(text)

    def playwright_click_and_wait(self, selector: str, wait_for: str = None, wait_timeout: int = 15000) -> str:
        if self._page is None:
            raise RuntimeError("Playwright page not initialized")
        self._page.click(selector)
        if wait_for:
            self._page.wait_for_selector(wait_for, timeout=wait_timeout)
        else:
            self._page.wait_for_timeout(3000)
        return self._page.content()

    @staticmethod
    def parse_html(html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "lxml")

    @staticmethod
    def clean_text(text: str) -> str:
        if not text:
            return ""
        return re.sub(r"\s+", " ", text).strip()

    def join_url(self, url: str) -> str:
        if url.startswith(("http://", "https://")):
            return url
        return urljoin(self.base_url, url)

    @staticmethod
    def extract_id_from_url(url: str, pattern: str = None) -> str:
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
