"""IGI/nbhd government interaction platform API crawler.

Multiple provinces use this same platform (Shaanxi, Shandong, Chongqing,
Guangxi, Qinghai). Each province just sets different siteId/appId.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from typing import Optional

from ..base_crawler import BaseCrawler
from ..models import ListItem, LetterRecord

TZ_CST = timezone(timedelta(hours=8))


def ts_to_date(ts) -> Optional[str]:
    """Convert Java-style millisecond timestamp to YYYY-MM-DD string."""
    if not ts:
        return None
    try:
        return datetime.fromtimestamp(int(ts) / 1000, tz=TZ_CST).strftime("%Y-%m-%d")
    except (ValueError, TypeError, OSError):
        return None


class IGIApiCrawler(BaseCrawler):
    """Base crawler for the IGI/nbhd openGovmsgbox platform.

    Subclasses set:
        igi_site_id: the siteId parameter
        igi_app_id:  the appId parameter (optional, some sites do not need it)
        igi_api_path: defaults to "/IGI/nbhd/openGovmsgbox.do"
    """

    igi_site_id: str = ""
    igi_app_id: str = ""
    igi_api_path: str = "/IGI/nbhd/openGovmsgbox.do"
    igi_order: str = "submitTime_desc"
    page_size: int = 15

    def _api_base(self) -> str:
        """Extract scheme+host from base_url."""
        from urllib.parse import urlparse
        parsed = urlparse(self.base_url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def fetch_list_page(self, page: int) -> list[ListItem]:
        """Fetch one page via the IGI/nbhd API."""
        api_url = self._api_base() + self.igi_api_path
        params = {
            "method": "listGovmsgboxs",
            "siteId": self.igi_site_id,
            "pageIndex": str(page),
            "pageSize": str(self.page_size),
            "order": "1",
            "orderBy": self.igi_order,
        }
        if self.igi_app_id:
            params["appId"] = self.igi_app_id

        result = self.playwright_get_json(
            api_url, params=params,
            headers={"Referer": self.base_url},
        )
        if result.get("statusCode") != 200:
            self.logger.warning(
                f"[{self.province}] IGI API returned statusCode={result.get('statusCode')}"
            )
            return []

        datas = result.get("datas") or {}
        items_raw = datas.get("data") or []
        return [self._parse_list_item(item) for item in items_raw]

    def fetch_detail(self, item: ListItem) -> LetterRecord:
        """Fetch detail. The IGI API list already contains full content,
        so we stored it in item metadata. If not available, fetch via URL."""
        # Try to use pre-loaded data from the list response
        if hasattr(item, "_raw_data") and item._raw_data:
            return self._build_record(item._raw_data, item)

        # Fallback: fetch the detail page HTML via Playwright (bypasses WAF)
        html = self.playwright_fetch(item.url)
        soup = self.parse_html(html)
        content = ""
        reply = ""
        for sel in [".content", ".mail-content", "#zoom", ".nr", ".article-content"]:
            el = soup.select_one(sel)
            if el:
                content = self.clean_text(el.get_text())
                break
        for sel in [".reply", ".huifu", ".answer", ".hf-nr", ".reply-content"]:
            el = soup.select_one(sel)
            if el:
                reply = self.clean_text(el.get_text())
                break
        return LetterRecord(
            province=self.province, title=item.title, url=item.url,
            original_id=item.original_id, content=content, reply_content=reply,
            publish_date=item.publish_date, reply_date=item.reply_date,
        )

    def _parse_list_item(self, raw: dict) -> ListItem:
        """Parse one API item into a ListItem, caching raw data for detail fetch."""
        title = raw.get("TITLE") or raw.get("title") or ""
        metadata_id = str(raw.get("METADATAID") or raw.get("metadataId") or "")
        publish_url = raw.get("PUBLISHURL") or ""

        # PUBLISHURL can be a JSON string or plain URL
        url = ""
        if publish_url:
            if publish_url.startswith("["):
                try:
                    url = json.loads(publish_url)[0].get("PUBLISHURL", "")
                except (json.JSONDecodeError, IndexError, TypeError):
                    url = ""
            else:
                url = publish_url
        if not url and metadata_id:
            url = f"{self._api_base()}/hd/ldxx/detail.html?metadataId={metadata_id}"

        pub_date = ts_to_date(raw.get("SUBMITTIME"))
        reply_date = ts_to_date(raw.get("REPLYTIME"))

        item = ListItem(
            title=title.strip(),
            url=url,
            original_id=metadata_id or title,
            publish_date=pub_date,
            reply_date=reply_date,
        )
        # Cache raw data so fetch_detail can use it without an extra request
        item._raw_data = raw  # type: ignore[attr-defined]
        return item

    def _build_record(self, raw: dict, item: ListItem) -> LetterRecord:
        """Build a LetterRecord from the raw API data (no extra HTTP request needed)."""
        content = raw.get("CONTENT") or raw.get("content") or ""
        # REPLYS is a list of reply objects
        reply = ""
        replys = raw.get("REPLYS")
        if isinstance(replys, list) and replys:
            reply = replys[0].get("CONTENT") or replys[0].get("content") or ""
        elif isinstance(replys, str):
            reply = replys

        return LetterRecord(
            province=self.province,
            title=item.title,
            url=item.url,
            original_id=item.original_id,
            content=self.clean_text(content),
            reply_content=self.clean_text(reply),
            publish_date=item.publish_date,
            reply_date=item.reply_date,
        )
