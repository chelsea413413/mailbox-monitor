"""anhui province crawler.

Site: https://sthjt.ah.gov.cn/zmhd/zxts/index.html
Method: HTTP + BeautifulSoup (static guestbook table)
"""
from __future__ import annotations

from .generic_http import GenericHttpCrawler


class AnhuiCrawler(GenericHttpCrawler):
    """Anhui province environment department mailbox crawler."""

    # List page: ul.odd and ul.even rows with li.t0-t5 cells
    list_container = "ul.odd, ul.even"
    list_title_sel = "li.t1 a"
    list_url_sel = "li.t1 a"
    list_url_attr = "href"
    list_date_sel = "li.t3"
    list_date_pattern = r"\d{4}[-/]\d{1,2}[-/]\d{1,2}"

    pagination_type = "path"
    pagination_path_tpl = "index_{page}.html"

    # Detail page selectors
    detail_title_sel = "h1, .title, .article-title"
    detail_content_sel = ".content, .nr, .article-content, #zoom, .wysz-content"
    detail_reply_sel = ".reply, .huifu, .answer, .hf-nr, .reply-content"
    detail_publish_date_sel = ".date, .publish-date, .info span"
    detail_reply_date_sel = ".reply-date, .hf-date"
    detail_date_pattern = r"\d{4}[-/]\d{1,2}[-/]\d{1,2}"

    id_pattern = r"/article/(\d+)"
