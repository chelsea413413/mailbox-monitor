"""gansu province crawler.

Site: https://sthj.gansu.gov.cn/sthj/c113082/lyzx.shtml
Method: Playwright (JS rendering required)
"""
from __future__ import annotations

from .playwright_crawler import PlaywrightCrawler


class GansuCrawler(PlaywrightCrawler):
    """gansu province environment department mailbox crawler."""

    list_container = "ul.list li, .news_list li, table tr"
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

    pw_wait_selector = "ul.list, .news_list, table"
    pw_wait_timeout = 20000

    id_pattern = r"/(\d+)/"
