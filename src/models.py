"""统一数据模型定义。

所有省份的采集适配器最终输出 LetterRecord，
下游差异引擎、数据库、报告生成器均基于此模型工作。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class RecordStatus(str, Enum):
    """记录与历史数据的比对结果。"""
    NEW = "new"
    UPDATED = "updated"
    UNCHANGED = "unchanged"


class CrawlStatus(str, Enum):
    """单省采集运行结果。"""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    NO_NEW = "no_new"


@dataclass
class ListItem:
    """列表页解析出的单条条目。"""
    title: str
    url: str
    original_id: str = ""
    publish_date: Optional[str] = None
    reply_date: Optional[str] = None


@dataclass
class LetterRecord:
    """标准化信件记录 - 全系统统一数据结构。"""
    province: str
    title: str
    url: str
    original_id: str
    content: str = ""
    reply_content: str = ""
    publish_date: Optional[str] = None
    reply_date: Optional[str] = None
    content_hash: str = ""
    status: RecordStatus = RecordStatus.NEW
    first_seen: str = ""
    last_updated: str = ""

    def compute_hash(self) -> str:
        """根据核心内容字段计算 SHA-256，用于检测内容更新。"""
        import hashlib
        raw = "|".join([
            self.title.strip(),
            self.content.strip(),
            self.reply_content.strip(),
            self.publish_date or "",
            self.reply_date or "",
        ])
        self.content_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return self.content_hash


@dataclass
class CrawlResult:
    """单省单次采集的完整结果。"""
    province: str
    province_id: str
    status: CrawlStatus = CrawlStatus.SUCCESS
    records: list[LetterRecord] = field(default_factory=list)
    new_count: int = 0
    updated_count: int = 0
    unchanged_count: int = 0
    total_found: int = 0
    error_message: str = ""
    duration_seconds: float = 0.0
    structure_alert: bool = False
    structure_alert_message: str = ""

    @property
    def has_changes(self) -> bool:
        return self.new_count > 0 or self.updated_count > 0

    @property
    def changed_records(self) -> list[LetterRecord]:
        return [r for r in self.records if r.status in (RecordStatus.NEW, RecordStatus.UPDATED)]


def now_iso() -> str:
    """当前 UTC 时间 ISO 字符串。"""
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def today_str() -> str:
    """当天日期字符串 YYYY-MM-DD（北京时间）。"""
    from datetime import timezone, timedelta
    tz_cst = timezone(timedelta(hours=8))
    return datetime.now(tz_cst).strftime("%Y-%m-%d")
