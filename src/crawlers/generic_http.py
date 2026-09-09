"""Generic HTTP crawler with configurable CSS selectors.

Most province sites are server-rendered HTML scraped via httpx + bs4.
Each province adapter subclasses this and sets selector attributes.
"""
from __future__ import annotations

import re
from typing import Optional

from ..base_crawler import BaseCrawler
from ..models import ListItem, LetterRecord


class GenericHttpCrawler(BaseCrawler):
    """Configurable HTTP crawler. Subclasses set selector attributes."""

    list_container: str = "ul li"
    list_title_sel: str = "a"
    list_url_sel: str = "a"
    list_url_attr: str = "href"
    list_date_sel: str = "span"
    list_date_pattern: Optional[str] = None

    pagination_type: str = "path"
    pagination_param: str = "page"
    pagination_path_tpl: str = "index_{page}.html"

    detail_title_sel: str = "h1"
    detail_content_sel: str = ".content"
    detail_reply_sel: str = ".reply"
    detail_publish_date_sel: str = ".publish-date"
    detail_reply_date_sel: str = ".reply-date"
    detail_date_pattern: Optional[str] = None

    id_pattern: Optional[str] = None
    force_encoding: Optional[str] = None

    def fetch_list_page(self, page: int) -> list[ListItem]:
        url = self._build_list_url(page)
        html = self.http_get(url)
        soup = self.parse_html(html)
        return self._parse_list(soup)

    def fetch_detail(self, item: ListItem) -> LetterRecord:
        html = self.http_get(item.url)
        soup = self.parse_html(html)
        return self._parse_detail(soup, item)

    def _build_list_url(self, page: int) -> str:
        if page <= 1 or self.pagination_type == "none":
            return self.base_url
        if self.pagination_type == "param":
            sep = "&" if "?" in self.base_url else "?"
            return f"{self.base_url}{sep}{self.pagination_param}={page}"
        if self.pagination_type == "path":
            base = self.base_url.split("?")[0]
            if base.endswith("/"):
                base = base + "index.html"
            directory = base.rsplit("/", 1)[0] + "/"
            return directory + self.pagination_path_tpl.format(page=page)
        return self.base_url

    def _parse_list(self, soup) -> list[ListItem]:
        items: list[ListItem] = []
        for row in soup.select(self.list_container):
            title_el = row.select_one(self.list_title_sel)
            if not title_el:
                continue
            title = self.clean_text(title_el.get_text())
            if not title:
                continue

            url_el = row.select_one(self.list_url_sel)
            url = ""
            if url_el:
                url = url_el.get(self.list_url_attr, "") or url_el.get("href", "")
            url = self.join_url(url) if url else ""

            date_str = None
            if self.list_date_sel:
                date_el = row.select_one(self.list_date_sel)
                if date_el:
                    date_str = self.clean_text(date_el.get_text())
                    if self.list_date_pattern:
                        m = re.search(self.list_date_pattern, date_str)
                        if m:
                            date_str = m.group(0)

            original_id = self.extract_id_from_url(url, self.id_pattern) if url else title
            items.append(ListItem(
                title=title, url=url, original_id=original_id, publish_date=date_str,
            ))
        return items

    def _parse_detail(self, soup, item: ListItem) -> LetterRecord:
        title = item.title
        if self.detail_title_sel:
            el = soup.select_one(self.detail_title_sel)
            if el:
                title = self.clean_text(el.get_text()) or title

        content = ""
        if self.detail_content_sel:
            el = soup.select_one(self.detail_content_sel)
            if el:
                content = self.clean_text(el.get_text())

        reply = ""
        if self.detail_reply_sel:
            el = soup.select_one(self.detail_reply_sel)
            if el:
                reply = self.clean_text(el.get_text())

        pub_date = item.publish_date
        if self.detail_publish_date_sel:
            el = soup.select_one(self.detail_publish_date_sel)
            if el:
                pub_date = self.clean_text(el.get_text()) or pub_date

        reply_date = None
        if self.detail_reply_date_sel:
            el = soup.select_one(self.detail_reply_date_sel)
            if el:
                reply_date = self.clean_text(el.get_text())

        return LetterRecord(
            province=self.province, title=title, url=item.url,
            original_id=item.original_id, content=content,
            reply_content=reply, publish_date=pub_date, reply_date=reply_date,
        )
