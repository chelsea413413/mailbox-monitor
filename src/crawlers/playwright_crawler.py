"""Playwright-based crawler for JavaScript-rendered pages.

Used by provinces whose list pages are loaded dynamically via JS,
or where HTTP requests are blocked by WAF/SSL issues.
"""
from __future__ import annotations

import re
from typing import Optional

from .generic_http import GenericHttpCrawler
from ..models import ListItem, LetterRecord


class PlaywrightCrawler(GenericHttpCrawler):
    """Crawler that uses Playwright for list page rendering, then HTTP for details.

    Subclasses set the same selector attributes as GenericHttpCrawler,
    plus optionally:
        pw_wait_selector: CSS selector to wait for before parsing list
        pw_wait_timeout:  timeout in ms (default 15000)
    """

    pw_wait_selector: str = ""
    pw_wait_timeout: int = 15000

    def fetch_list_page(self, page: int) -> list[ListItem]:
        """Render the list page with Playwright, then parse the HTML."""
        url = self._build_list_url(page)
        html = self.playwright_fetch(
            url,
            wait_for=self.pw_wait_selector or None,
            wait_timeout=self.pw_wait_timeout,
        )
        soup = self.parse_html(html)
        return self._parse_list(soup)

    def fetch_detail(self, item: ListItem) -> LetterRecord:
        """Fetch detail page. Try HTTP first, fall back to Playwright on error."""
        try:
            html = self.http_get(item.url)
            soup = self.parse_html(html)
            record = self._parse_detail(soup, item)
            if record.content or record.reply_content:
                return record
        except Exception:
            pass

        # Fallback: use Playwright for detail page
        html = self.playwright_fetch(
            item.url,
            wait_for=self.pw_wait_selector or None,
            wait_timeout=self.pw_wait_timeout,
        )
        soup = self.parse_html(html)
        return self._parse_detail(soup, item)
