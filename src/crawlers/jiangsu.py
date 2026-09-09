"""江苏省长信箱采集适配器。

网站: http://sthjt.jiangsu.gov.cn/jact/front/mailpublist.do?sysid=143
采集方式: API (jact 政民互动平台)
独立文件 - 网站改版时只需修改此文件。
"""
from __future__ import annotations

import re

from ..base_crawler import BaseCrawler
from ..models import ListItem, LetterRecord


class JiangsuCrawler(BaseCrawler):
    """江苏省生态环境厅厅长信箱采集器 (jact API)。"""

    # jact 平台通常通过 POST 请求获取列表
    API_URL = "http://sthjt.jiangsu.gov.cn/jact/front/mailpublist.do"
    SYSID = "143"
    PAGE_SIZE = 15

    def fetch_list_page(self, page: int) -> list[ListItem]:
        """通过 jact API 获取信件列表。"""
        params = {
            "sysid": self.SYSID,
            "page": page,
            "pageSize": self.PAGE_SIZE,
        }
        data = self.http_post(self.API_URL, data=params)
        import json
        try:
            result = json.loads(data)
        except (json.JSONDecodeError, ValueError):
            result = {}

        items: list[ListItem] = []
        mail_list = result.get("mailList") or result.get("rows") or result.get("data") or []
        if isinstance(mail_list, dict):
            mail_list = mail_list.get("list", [])

        for entry in mail_list:
            title = entry.get("title") or entry.get("mailTitle") or ""
            mail_id = str(entry.get("mailid") or entry.get("id") or entry.get("mailId") or "")
            url = entry.get("url") or entry.get("link") or ""
            if not url and mail_id:
                url = f"http://sthjt.jiangsu.gov.cn/jact/front/mailpubdetail.do?sysid={self.SYSID}&mailid={mail_id}"
            pub_date = entry.get("createdate") or entry.get("publishDate") or entry.get("createTime") or None
            reply_date = entry.get("replydate") or entry.get("replyDate") or None

            if title:
                items.append(ListItem(
                    title=title.strip(),
                    url=url,
                    original_id=mail_id or title,
                    publish_date=pub_date,
                    reply_date=reply_date,
                ))
        return items

    def fetch_detail(self, item: ListItem) -> LetterRecord:
        """获取信件详情页内容。"""
        html = self.http_get(item.url)
        soup = self.parse_html(html)

        title = item.title
        title_el = soup.select_one("h1, .title, .mail-title")
        if title_el:
            title = self.clean_text(title_el.get_text()) or title

        content = ""
        content_el = soup.select_one(".mail-content, .content, #mailcontent, .nr")
        if content_el:
            content = self.clean_text(content_el.get_text())

        reply = ""
        reply_el = soup.select_one(".reply-content, .huifu, .answer, .hf-nr")
        if reply_el:
            reply = self.clean_text(reply_el.get_text())

        return LetterRecord(
            province=self.province,
            title=title,
            url=item.url,
            original_id=item.original_id,
            content=content,
            reply_content=reply,
            publish_date=item.publish_date,
            reply_date=item.reply_date,
        )
