"""hunan province crawler.

Site: http://sthjt.hunan.gov.cn/sthjt/hdjl/zxts/97514/index.html
Method: Playwright (bypasses WAF, renders JS if needed)
"""
from __future__ import annotations

from .playwright_crawler import PlaywrightCrawler


class HunanCrawler(PlaywrightCrawler):
    """Hunan province environment department mailbox crawler."""

    list_container = ".news_list li, .list li, ul.list li, table tr"
    list_title_sel = "a"
    list_url_sel = "a"
    list_url_attr = "href"
    list_date_sel = "span, td.date, .date"
    list_date_pattern = r"\d{4}[-/]\d{1,2}[-/]\d{1,2}"

    pagination_type = "path"
    pagination_path_tpl = "index_{page}.html"

    pw_wait_selector = ".news_list li, .list li, ul.list li, table tr"
    pw_wait_timeout = 20000

    detail_title_sel = "h1, .title, .article-title"
    detail_content_sel = ".content, .nr, .article-content, #zoom"
    detail_reply_sel = ".reply, .huifu, .answer, .hf-nr"
    detail_publish_date_sel = ".date, .publish-date, .info span"
    detail_reply_date_sel = ".reply-date, .hf-date"
    detail_date_pattern = r"\d{4}[-/]\d{1,2}[-/]\d{1,2}"

    id_pattern = r"/(\d+)/?"