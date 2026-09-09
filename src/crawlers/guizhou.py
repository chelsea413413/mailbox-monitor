"""贵州省厅长信箱采集适配器。

网站: https://sthj.guizhou.gov.cn/hdjl/
采集方式: HTTP + BeautifulSoup
独立文件 - 网站改版时只需修改此文件中的选择器配置。
"""
from __future__ import annotations

from .generic_http import GenericHttpCrawler


class GuizhouCrawler(GenericHttpCrawler):
    """贵州省生态环境厅厅长信箱采集器。"""

    # 列表页选择器 - 根据实际网站结构调整
    list_container = ".news_list li, .list li, ul.list li, table tr"
    list_title_sel = "a"
    list_url_sel = "a"
    list_url_attr = "href"
    list_date_sel = "span, td.date, .date"
    list_date_pattern = r"\d{4}[-/]\d{1,2}[-/]\d{1,2}"

    # 分页方式: path(index_2.html) / param(?page=2) / none
    pagination_type = "path"
    pagination_path_tpl = "index_{page}.html"

    # 详情页选择器 - 根据实际网站结构调整
    detail_title_sel = "h1, .title, .article-title"
    detail_content_sel = ".content, .nr, .article-content, #zoom"
    detail_reply_sel = ".reply, .huifu, .answer, .hf-nr"
    detail_publish_date_sel = ".date, .publish-date, .info span"
    detail_reply_date_sel = ".reply-date, .hf-date"
    detail_date_pattern = r"\d{4}[-/]\d{1,2}[-/]\d{1,2}"

    # 从详情页URL中提取原始ID的正则
    id_pattern = r"/(\d+)/?"
