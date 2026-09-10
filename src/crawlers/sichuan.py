"""sichuan province crawler.

Site: https://sthjt.sc.gov.cn/sthjt/c103053/newldxx.shtml
Method: HTTP + BeautifulSoup (static table)
"""
from __future__ import annotations

from .generic_http import GenericHttpCrawler


class SichuanCrawler(GenericHttpCrawler):
    """Sichuan province environment department mailbox crawler."""

    # List page: table#newldxx with tr rows, 5 td cells each
    list_container = "table#newldxx tr"
    list_title_sel = "td:nth-child(2) a"
    list_url_sel = "td:nth-child(2) a"
    list_url_attr = "href"
    list_date_sel = "td:nth-child(3)"
    list_date_pattern = r"\d{4}[-/]\d{1,2}[-/]\d{1,2}"

    pagination_type = "none"

    # Detail page selectors
    detail_title_sel = "h1, .title, .article-title"
    detail_content_sel = ".content, .nr, .article-content, #zoom, .mail-content"
    detail_reply_sel = ".reply, .huifu, .answer, .hf-nr, .reply-content"
    detail_publish_date_sel = ".date, .publish-date, .info span"
    detail_reply_date_sel = ".reply-date, .hf-date"
    detail_date_pattern = r"\d{4}[-/]\d{1,2}[-/]\d{1,2}"

    id_pattern = r"mailId=(\d+)"
