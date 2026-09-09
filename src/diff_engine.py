"""差异引擎：基于 original_id + content_hash 比对历史数据。

核心逻辑：
- original_id 在历史库中不存在 -> NEW
- original_id 存在但 content_hash 不同 -> UPDATED
- original_id 存在且 content_hash 相同 -> UNCHANGED
"""
from __future__ import annotations

from typing import Iterable

from .models import LetterRecord, RecordStatus


def classify_records(
    new_records: list[LetterRecord],
    existing: dict[str, str],
) -> list[LetterRecord]:
    """将新采集的记录与历史库比对，标记 status。

    Args:
        new_records: 本次采集的记录列表
        existing: {original_id: content_hash} 历史快照

    Returns:
        标注好 status 的记录列表（原地修改）
    """
    for record in new_records:
        if not record.content_hash:
            record.compute_hash()

        old_hash = existing.get(record.original_id)
        if old_hash is None:
            record.status = RecordStatus.NEW
        elif old_hash != record.content_hash:
            record.status = RecordStatus.UPDATED
        else:
            record.status = RecordStatus.UNCHANGED

    return new_records


def summarize(records: Iterable[LetterRecord]) -> dict:
    """统计 NEW / UPDATED / UNCHANGED 数量。"""
    counts = {"new": 0, "updated": 0, "unchanged": 0}
    for r in records:
        counts[r.status.value] = counts.get(r.status.value, 0) + 1
    return counts
