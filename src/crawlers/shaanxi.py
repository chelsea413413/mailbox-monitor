"""陕西省长信箱采集适配器。

网站: https://sthjt.shaanxi.gov.cn/hd/ldxx/xd/
采集方式: IGI/nbhd API (siteId=167, appId=50)
独立文件 - 网站改版时只需修改此文件。
"""
from __future__ import annotations

from .igi_api import IGIApiCrawler


class ShaanxiCrawler(IGIApiCrawler):
    """陕西省生态环境厅厅长信箱采集器 (IGI/nbhd API)。"""

    igi_site_id = "167"
    igi_app_id = "50"
