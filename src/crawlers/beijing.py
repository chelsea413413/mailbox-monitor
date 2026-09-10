"""beijing province crawler.

Site: https://sthjj.beijing.gov.cn/hudong/xinxiang/sthjj/sindex/xx-sthjj.html
Method: Playwright (JS rendering required)
"""
from __future__ import annotations

from .playwright_crawler import PlaywrightCrawler


class BeijingCrawler(PlaywrightCrawler):
    """Beijing municipality environment department mailbox crawler."""

    list_container = "ul.list li, table tr, .mail-list li, .common-list li"
    list_title_sel = "a"
    list_url_sel = "a"
    list_url_attr = "href"
    list_date_sel = "span, .date, td:nth-child(3)"
    list_date_pattern = r"\d{4}[-/]\d{1,2}[-/]\d{1,2}"

    pagination_type = "none"

    detail_title_sel = "h1, .title, .article-title, .mail-title"
    detail_content_sel = ".content, .nr, .article-content, #zoom, .mail-content, .question"
    detail_reply_sel = ".reply, .huifu, .answer, .hf-nr, .reply-content"
    detail_publish_date_sel = ".date, .publish-date, .info span, .time"
    detail_reply_date_sel = ".reply-date, .hf-date, .reply-time"
    detail_date_pattern = r"\d{4}[-/]\d{1,2}[-/]\d{1,2}"

    pw_wait_selector = "ul.list li, table tr, .mail-list li, .common-list li"
    pw_wait_timeout = 20000

    id_pattern = r"/(\d+)"
