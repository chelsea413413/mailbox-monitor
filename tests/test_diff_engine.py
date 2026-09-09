"""Tests for the diff engine."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.models import LetterRecord, RecordStatus
from src.diff_engine import classify_records, summarize


def make_record(province, oid, title="T", content="C", reply="R"):
    r = LetterRecord(
        province=province, title=title, url=f"http://x/{oid}",
        original_id=oid, content=content, reply_content=reply,
    )
    r.compute_hash()
    return r


def test_new_record():
    records = [make_record("Sichuan", "1")]
    result = classify_records(records, {})
    assert result[0].status == RecordStatus.NEW


def test_unchanged_record():
    r = make_record("Sichuan", "1")
    existing = {"1": r.content_hash}
    result = classify_records([r], existing)
    assert result[0].status == RecordStatus.UNCHANGED


def test_updated_record():
    r1 = make_record("Sichuan", "1", content="old")
    existing = {"1": r1.content_hash}
    r2 = make_record("Sichuan", "1", content="new content")
    result = classify_records([r2], existing)
    assert result[0].status == RecordStatus.UPDATED


def test_summarize():
    records = [
        make_record("A", "1"),
        make_record("A", "2", content="x"),
        make_record("A", "3"),
    ]
    existing = {"1": records[0].content_hash, "2": records[1].content_hash}
    classified = classify_records(records, existing)
    summary = summarize(classified)
    assert summary["new"] == 1
    assert summary["unchanged"] == 2


if __name__ == "__main__":
    test_new_record()
    test_unchanged_record()
    test_updated_record()
    test_summarize()
    print("All diff engine tests passed!")
