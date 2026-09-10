"""henan province crawler.

Site: https://sthjt.henan.gov.cn/hdjl/wyzxldxx/list/
Method: HTTP + BeautifulSoup (static newslist)
"""
from __future__ import annotations

from .generic_http import GenericHttpCrawler


class HenanCrawler(GenericHttpCrawler):
    """Henan province environment department mailbox crawler."""

    # List page: ul.newslist with li items
    list_container = "ul.newslist li, .newsList ul li"
    list_title_sel = "a"
    list_url_sel = "a"
    list_url_attr = "href"
    list_date_sel = "span, .date"
    list_date_pattern = r"\d{4}[-/]\d{1,2}[-/]\d{1,2}"

    pagination_type = "none"

    # Detail page selectors (wenda.henan.gov.cn platform)
    detail_title_sel = "h1, .title, .question-title, .wysz-title"
    detail_content_sel = ".content, .question-content, .wysz-content, .consult-content, #zoom"
    detail_reply_sel = ".reply, .answer, .reply-content, .hf-nr, .huifu"
    detail_publish_date_sel = ".date, .publish-date, .info span, .time"
    detail_reply_date_sel = ".reply-date, .hf-date, .reply-time"
    detail_date_pattern = r"\d{4}[-/]\d{1,2}[-/]\d{1,2}"

    id_pattern = r"/pc/([A-F0-9]+)"
