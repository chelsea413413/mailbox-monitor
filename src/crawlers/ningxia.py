"""宁夏厅长信箱采集适配器。

网站: https://app.12345.nx.gov.cn/cns-bmfw-webrest/pages/Leader/service_openlist
采集方式: API (12345 政务服务平台)
独立文件 - 网站改版时只需修改此文件。
"""
from __future__ import annotations

import json

from ..base_crawler import BaseCrawler
from ..models import ListItem, LetterRecord


class NingxiaCrawler(BaseCrawler):
    """宁夏生态环境厅厅长信箱采集器 (12345 平台 API)。"""

    API_BASE = "https://app.12345.nx.gov.cn/cns-bmfw-webrest"
    LIST_API = API_BASE + "/api/Leader/serviceOpenList"
    DETAIL_API = API_BASE + "/api/Leader/serviceDetail"
    EMAIL_FLAG = "29"
    DEPT_GUID = "46166aa4-792c-4f05-a315-abd04c14f4ff"
    PAGE_SIZE = 10

    def fetch_list_page(self, page: int) -> list[ListItem]:
        """通过 12345 平台 API 获取信件列表。"""
        params = {
            "emailFlag": self.EMAIL_FLAG,
            "deptGuid": self.DEPT_GUID,
            "pageNo": page,
            "pageSize": self.PAGE_SIZE,
        }
        try:
            result = self.playwright_get_json(self.LIST_API, params=params)
        except Exception:
            result = {}

        items: list[ListItem] = []
        data = result.get("data") or result
        if isinstance(data, dict):
            rows = data.get("list") or data.get("rows") or data.get("records") or []
        elif isinstance(data, list):
            rows = data
        else:
            rows = []

        for entry in rows:
            title = entry.get("title") or entry.get("questionTitle") or entry.get("content") or ""
            item_id = str(entry.get("id") or entry.get("serviceId") or entry.get("guid") or "")
            url = entry.get("url") or ""
            if not url and item_id:
                url = f"{self.API_BASE}/pages/Leader/serviceDetail?id={item_id}"
            pub_date = entry.get("createTime") or entry.get("createdTime") or None
            reply_date = entry.get("replyTime") or entry.get("answerTime") or None

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
        """获取信件详情。"""
        content = ""
        reply = ""
        pub_date = item.publish_date
        reply_date = item.reply_date

        try:
            params = {"id": item.original_id, "deptGuid": self.DEPT_GUID}
            result = self.playwright_get_json(self.DETAIL_API, params=params)
            detail = result.get("data") or result
            if isinstance(detail, dict):
                content = detail.get("content") or detail.get("questionContent") or ""
                reply = detail.get("replyContent") or detail.get("answer") or detail.get("reply") or ""
                pub_date = detail.get("createTime") or pub_date
                reply_date = detail.get("replyTime") or reply_date
        except Exception:
            pass

        if not content or not reply:
            try:
                html = self.playwright_fetch(item.url)
                soup = self.parse_html(html)
                if not content:
                    el = soup.select_one(".content, .question-content, .consult")
                    if el:
                        content = self.clean_text(el.get_text())
                if not reply:
                    el = soup.select_one(".reply, .answer, .reply-content")
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
