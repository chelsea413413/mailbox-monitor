"""Database layer (SQLite).

Three core tables:
  letters          - main record table, unique on (province, original_id)
  crawl_logs       - per-run crawl execution log
  structure_alerts - website structure change alerts
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from .models import CrawlResult, LetterRecord, RecordStatus, now_iso, today_str


SCHEMA = """
CREATE TABLE IF NOT EXISTS letters (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    province      TEXT NOT NULL,
    original_id   TEXT NOT NULL,
    title         TEXT,
    url           TEXT,
    publish_date  TEXT,
    reply_date    TEXT,
    content       TEXT,
    reply_content TEXT,
    content_hash  TEXT NOT NULL,
    first_seen    TEXT NOT NULL,
    last_updated  TEXT NOT NULL,
    last_checked  TEXT NOT NULL,
    UNIQUE(province, original_id)
);

CREATE INDEX IF NOT EXISTS idx_letters_province ON letters(province);
CREATE INDEX IF NOT EXISTS idx_letters_hash ON letters(province, content_hash);

CREATE TABLE IF NOT EXISTS crawl_logs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    province         TEXT NOT NULL,
    run_date         TEXT NOT NULL,
    status           TEXT NOT NULL,
    items_found      INTEGER DEFAULT 0,
    items_new        INTEGER DEFAULT 0,
    items_updated    INTEGER DEFAULT 0,
    error_message    TEXT,
    duration_seconds REAL,
    structure_alert  INTEGER DEFAULT 0,
    created_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS structure_alerts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    province   TEXT NOT NULL,
    alert_date TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    message    TEXT,
    resolved   INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);
"""


class Database:
    """SQLite database wrapper."""

    def __init__(self, db_path: str = "data/mailbox.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def init_db(self) -> None:
        """Create tables (idempotent)."""
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def get_existing_hashes(self, province: str) -> dict[str, str]:
        """Get {original_id: content_hash} snapshot for a province."""
        rows = self.conn.execute(
            "SELECT original_id, content_hash FROM letters WHERE province = ?",
            (province,),
        ).fetchall()
        return {row["original_id"]: row["content_hash"] for row in rows}

    def upsert_record(self, record: LetterRecord) -> RecordStatus:
        """Insert or update a single record, return its status."""
        now = now_iso()
        if record.status == RecordStatus.NEW:
            self.conn.execute(
                """INSERT INTO letters
                   (province, original_id, title, url, publish_date, reply_date,
                    content, reply_content, content_hash,
                    first_seen, last_updated, last_checked)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (record.province, record.original_id, record.title, record.url,
                 record.publish_date, record.reply_date,
                 record.content, record.reply_content, record.content_hash,
                 now, now, now),
            )
        elif record.status == RecordStatus.UPDATED:
            self.conn.execute(
                """UPDATE letters SET
                     title=?, url=?, publish_date=?, reply_date=?,
                     content=?, reply_content=?, content_hash=?,
                     last_updated=?, last_checked=?
                   WHERE province=? AND original_id=?""",
                (record.title, record.url, record.publish_date, record.reply_date,
                 record.content, record.reply_content, record.content_hash,
                 now, now, record.province, record.original_id),
            )
        else:
            self.conn.execute(
                "UPDATE letters SET last_checked=? WHERE province=? AND original_id=?",
                (now, record.province, record.original_id),
            )
        return record.status

    def save_crawl_log(self, result: CrawlResult) -> None:
        """Log this crawl run."""
        self.conn.execute(
            """INSERT INTO crawl_logs
               (province, run_date, status, items_found, items_new, items_updated,
                error_message, duration_seconds, structure_alert, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (result.province, today_str(), result.status.value,
             result.total_found, result.new_count, result.updated_count,
             result.error_message, result.duration_seconds,
             int(result.structure_alert), now_iso()),
        )
        self.conn.commit()

    def save_structure_alert(
        self, province: str, alert_type: str, message: str
    ) -> None:
        """Record a website structure change alert."""
        self.conn.execute(
            """INSERT INTO structure_alerts
               (province, alert_date, alert_type, message, resolved, created_at)
               VALUES (?, ?, ?, ?, 0, ?)""",
            (province, today_str(), alert_type, message, now_iso()),
        )
        self.conn.commit()

    def get_today_changes(self) -> list[sqlite3.Row]:
        """Get records changed today (new + updated)."""
        return self.conn.execute(
            """SELECT * FROM letters
               WHERE date(last_updated) = date(?)
               ORDER BY province, last_updated DESC""",
            (today_str(),),
        ).fetchall()

    def get_recent_structure_alerts(self, days: int = 7) -> list[sqlite3.Row]:
        """Get unresolved structure alerts from the last N days."""
        return self.conn.execute(
            """SELECT * FROM structure_alerts
               WHERE resolved = 0
                 AND date(created_at) >= date('now', ?)
               ORDER BY created_at DESC""",
            (f"-{days} days",),
        ).fetchall()

    def close(self) -> None:
        if self._conn:
            self._conn.commit()
            self._conn.close()
            self._conn = None
