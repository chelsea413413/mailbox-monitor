"""tianjin province crawler.

Site: https://sthj.tj.gov.cn/ZMHD5922/ZMLJL3913/
Method: Playwright (JS rendering required)
"""
from __future__ import annotations

from .playwright_crawler import PlaywrightCrawler


class TianjinCrawler(PlaywrightCrawler):
    """tianjin province environment department mailbox crawler."""

    list_container = "ul.common-list li, table tr"
    list_title_sel = "a"
    list_url_sel = "a"
    list_url_attr = "href"
    list_date_sel = "span, .date"
    list_date_pattern = r"\d{4}[-/]\d{1,2}[-/]\d{1,2}"

    pagination_type = "none"

    detail_title_sel = "h1, .title, .article-title, .mail-title"
    detail_content_sel = ".content, .nr, .article-content, #zoom, .mail-content, .question"
    detail_reply_sel = ".reply, .huifu, .answer, .hf-nr, .reply-content"
    detail_publish_date_sel = ".date, .publish-date, .info span, .time"
    detail_reply_date_sel = ".reply-date, .hf-date, .reply-time"
    detail_date_pattern = r"\d{4}[-/]\d{1,2}[-/]\d{1,2}"

    pw_wait_selector = "ul.common-list, table"
    pw_wait_timeout = 20000

    id_pattern = r"id=(\d+)"
