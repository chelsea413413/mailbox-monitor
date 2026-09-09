"""Tests for the database layer."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database import Database
from src.models import LetterRecord, RecordStatus, CrawlResult, CrawlStatus


def test_init_and_upsert():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(str(Path(tmpdir) / "test.db"))
        db.init_db()

        # Insert new record
        r = LetterRecord(
            province="Test", title="T1", url="http://x/1",
            original_id="1", content="C1", reply_content="R1",
        )
        r.compute_hash()
        r.status = RecordStatus.NEW
        db.upsert_record(r)
        db.conn.commit()

        # Verify
        hashes = db.get_existing_hashes("Test")
        assert "1" in hashes
        assert hashes["1"] == r.content_hash

        # Update record
        r2 = LetterRecord(
            province="Test", title="T1-updated", url="http://x/1",
            original_id="1", content="C1-new", reply_content="R1-new",
        )
        r2.compute_hash()
        r2.status = RecordStatus.UPDATED
        db.upsert_record(r2)
        db.conn.commit()

        hashes = db.get_existing_hashes("Test")
        assert hashes["1"] == r2.content_hash

        db.close()


def test_crawl_log():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(str(Path(tmpdir) / "test.db"))
        db.init_db()

        result = CrawlResult(
            province="Test", province_id="test",
            status=CrawlStatus.SUCCESS,
            total_found=5, new_count=2, updated_count=1,
            duration_seconds=12.5,
        )
        db.save_crawl_log(result)

        rows = db.conn.execute(
            "SELECT * FROM crawl_logs WHERE province = ?", ("Test",)
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["items_new"] == 2
        db.close()


if __name__ == "__main__":
    test_init_and_upsert()
    test_crawl_log()
    print("All database tests passed!")
