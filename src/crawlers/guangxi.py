"""广西省长信箱采集适配器。

网站: http://sthjt.gxzf.gov.cn/gxhd/ldxx/
采集方式: IGI/nbhd API (siteId=200, appId=1091)
独立文件 - 网站改版时只需修改此文件。
"""
from __future__ import annotations

from .igi_api import IGIApiCrawler


class GuangxiCrawler(IGIApiCrawler):
    """广西省生态环境厅厅长信箱采集器 (IGI/nbhd API)。"""

    igi_site_id = "200"
    igi_app_id = "1091"
