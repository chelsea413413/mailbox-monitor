"""广东省长信箱采集适配器。

网站: https://gdee.gd.gov.cn/hdjlpt/published?via=pc
采集方式: API (hdjlpt 互动交流平台)
独立文件 - 网站改版时只需修改此文件。
"""
from __future__ import annotations

import json

from ..base_crawler import BaseCrawler
from ..models import ListItem, LetterRecord


class GuangdongCrawler(BaseCrawler):
    """广东省生态环境厅厅长信箱采集器 (hdjlpt API)。"""

    # hdjlpt 平台 API 端点
    API_BASE = "https://gdee.gd.gov.cn/hdjlpt"
    LIST_API = API_BASE + "/api/published/list"
    DETAIL_API = API_BASE + "/api/published/detail"
    PAGE_SIZE = 15

    def fetch_list_page(self, page: int) -> list[ListItem]:
        """通过 hdjlpt API 获取已公开信件列表。"""
        params = {
            "page": page,
            "pageSize": self.PAGE_SIZE,
            "type": "leader",
        }
        try:
            result = self.http_get_json(self.LIST_API, params=params)
        except Exception:
            result = {}

        items: list[ListItem] = []
        data = result.get("data") or result
        if isinstance(data, dict):
            rows = data.get("list") or data.get("rows") or data.get("items") or []
        elif isinstance(data, list):
            rows = data
        else:
            rows = []

        for entry in rows:
            title = entry.get("title") or entry.get("question") or ""
            item_id = str(entry.get("id") or entry.get("mailId") or entry.get("questionId") or "")
            url = entry.get("url") or ""
            if not url and item_id:
                url = f"{self.API_BASE}/published/detail?via=pc&id={item_id}"
            pub_date = entry.get("createTime") or entry.get("created_at") or None
            reply_date = entry.get("replyTime") or entry.get("reply_time") or None

            if title:
                items.append(ListItem(
                    title=title.strip(),
                    url=url,
                    original_id=item_id or title,
                    publish_date=pub_date,
                    reply_date=reply_date,
                ))
        return items

    def fetch_detail(self, item: ListItem) -> LetterRecord:
        """获取信件详情。优先尝试API，失败则回退到网页解析。"""
        content = ""
        reply = ""
        pub_date = item.publish_date
        reply_date = item.reply_date

        # 尝试 API 获取详情
        try:
            params = {"id": item.original_id}
            result = self.http_get_json(self.DETAIL_API, params=params)
            detail = result.get("data") or result
            if isinstance(detail, dict):
                content = detail.get("content") or detail.get("question") or detail.get("consultContent") or ""
                reply = detail.get("replyContent") or detail.get("reply") or detail.get("answer") or ""
                pub_date = detail.get("createTime") or pub_date
                reply_date = detail.get("replyTime") or reply_date
        except Exception:
            pass

        # API 失败时回退到网页解析
        if not content or not reply:
            try:
                html = self.http_get(item.url)
                soup = self.parse_html(html)
                if not content:
                    el = soup.select_one(".content, .question, .consult-content, .wysz-content")
                    if el:
                        content = self.clean_text(el.get_text())
                if not reply:
                    el = soup.select_one(".reply, .answer, .reply-content, .hf-nr")
                    if el:
                        reply = self.clean_text(el.get_text())
            except Exception:
                pass

        return LetterRecord(
            province=self.province,
            title=item.title,
            url=item.url,
            original_id=item.original_id,
            content=content,
            reply_content=reply,
            publish_date=pub_date,
            reply_date=reply_date,
        )
