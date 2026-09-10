"""青海省长信箱采集适配器。

网站: https://sthjt.qinghai.gov.cn/hdjl/lyzx/list.html
采集方式: IGI/nbhd API (siteId=3, appId=无)
独立文件 - 网站改版时只需修改此文件。
"""
from __future__ import annotations

from .igi_api import IGIApiCrawler


class QinghaiCrawler(IGIApiCrawler):
    """青海省生态环境厅厅长信箱采集器 (IGI/nbhd API)。"""

    igi_site_id = "3"
    igi_app_id = ""
