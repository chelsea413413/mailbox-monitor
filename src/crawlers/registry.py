"""Crawler registry: maps province IDs to crawler classes."""
from __future__ import annotations

from typing import Type

from ..base_crawler import BaseCrawler

# HTTP-based crawlers
from .sichuan import SichuanCrawler
from .hunan import HunanCrawler
from .hubei import HubeiCrawler
from .guangxi import GuangxiCrawler
from .anhui import AnhuiCrawler
from .yunnan import YunnanCrawler
from .guizhou import GuizhouCrawler
from .shaanxi import ShaanxiCrawler
from .henan import HenanCrawler
from .hebei import HebeiCrawler
from .jiangxi import JiangxiCrawler
from .shandong import ShandongCrawler
from .heilongjiang import HeilongjiangCrawler
from .neimenggu import NeimengguCrawler
from .xinjiang import XinjiangCrawler
from .gansu import GansuCrawler
from .qinghai import QinghaiCrawler
from .fujian import FujianCrawler
from .chongqing import ChongqingCrawler
from .tianjin import TianjinCrawler
from .beijing import BeijingCrawler

# API-based crawlers
from .jiangsu import JiangsuCrawler
from .guangdong import GuangdongCrawler
from .ningxia import NingxiaCrawler


REGISTRY: dict[str, Type[BaseCrawler]] = {
    "sichuan": SichuanCrawler,
    "hunan": HunanCrawler,
    "hubei": HubeiCrawler,
    "jiangsu": JiangsuCrawler,
    "guangxi": GuangxiCrawler,
    "anhui": AnhuiCrawler,
    "yunnan": YunnanCrawler,
    "guizhou": GuizhouCrawler,
    "shaanxi": ShaanxiCrawler,
    "henan": HenanCrawler,
    "hebei": HebeiCrawler,
    "jiangxi": JiangxiCrawler,
    "shandong": ShandongCrawler,
    "heilongjiang": HeilongjiangCrawler,
    "neimenggu": NeimengguCrawler,
    "xinjiang": XinjiangCrawler,
    "gansu": GansuCrawler,
    "qinghai": QinghaiCrawler,
    "ningxia": NingxiaCrawler,
    "fujian": FujianCrawler,
    "guangdong": GuangdongCrawler,
    "chongqing": ChongqingCrawler,
    "tianjin": TianjinCrawler,
    "beijing": BeijingCrawler,
}


def get_crawler_class(province_id: str) -> Type[BaseCrawler]:
    """Look up the crawler class for a province ID."""
    if province_id not in REGISTRY:
        raise KeyError(f"No crawler registered for province '{province_id}'")
    return REGISTRY[province_id]
