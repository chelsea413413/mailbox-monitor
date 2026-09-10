"""山东省长信箱采集适配器。

网站: http://sthj.shandong.gov.cn/hdjl/zxzx/index.html
采集方式: IGI/nbhd API (siteId=33, appId=无)
独立文件 - 网站改版时只需修改此文件。
"""
from __future__ import annotations

from .igi_api import IGIApiCrawler


class ShandongCrawler(IGIApiCrawler):
    """山东省生态环境厅厅长信箱采集器 (IGI/nbhd API)。"""

    igi_site_id = "33"
    igi_app_id = ""
