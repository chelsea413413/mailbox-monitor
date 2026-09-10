"""重庆省长信箱采集适配器。

网站: https://sthjj.cq.gov.cn/hdjl_249/gkxx/lxxd/
采集方式: IGI/nbhd API (siteId=249, appId=81)
独立文件 - 网站改版时只需修改此文件。
"""
from __future__ import annotations

from .igi_api import IGIApiCrawler


class ChongqingCrawler(IGIApiCrawler):
    """重庆省生态环境厅厅长信箱采集器 (IGI/nbhd API)。"""

    igi_site_id = "249"
    igi_app_id = "81"
