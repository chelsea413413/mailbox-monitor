"""Main orchestrator: runs the daily crawl across all provinces.

Usage:
    python -m src.main                # run all provinces
    python -m src.main sichuan hunan  # run specific provinces only
    python -m src.main --dry-run      # crawl but skip email sending
"""
from __future__ import annotations

# Force IPv4 for all DNS lookups.  GitHub Actions runners have IPv6
# connectivity but Chinese government websites only serve over IPv4,
# causing "[Errno 101] Network is unreachable" when IPv6 is tried first.
import socket as _socket
_orig_getaddrinfo = _socket.getaddrinfo

def _ipv4_only_getaddrinfo(host, *args, **kwargs):
    results = _orig_getaddrinfo(host, *args, **kwargs)
    ipv4 = [r for r in results if r[0] == _socket.AF_INET]
    return ipv4 if ipv4 else results

_socket.getaddrinfo = _ipv4_only_getaddrinfo

import os
import sys
import time
from pathlib import Path

import yaml
from dotenv import load_dotenv

from .logger import setup_logger
from .database import Database
from .diff_engine import classify_records
from .excel_generator import generate_excel
from .email_reporter import render_html_report, send_email
from .models import CrawlResult, CrawlStatus, RecordStatus, today_str
from .crawlers.registry import get_crawler_class


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_config() -> tuple[dict, list[dict]]:
    """Load settings.yaml and provinces.yaml, expanding env vars."""
    load_dotenv(PROJECT_ROOT / "config" / ".env")

    with open(PROJECT_ROOT / "config" / "settings.yaml", encoding="utf-8") as f:
        settings = yaml.safe_load(f)

    with open(PROJECT_ROOT / "config" / "provinces.yaml", encoding="utf-8") as f:
        provinces_data = yaml.safe_load(f)

    return settings, provinces_data["provinces"]


def run_single_province(
    province_config: dict,
    settings: dict,
    db: Database,
    logger,
) -> CrawlResult:
    """Run the full crawl-diff-persist pipeline for one province."""
    province_id = province_config["id"]
    province_name = province_config["name"]
    logger.info(f"=== Starting crawl: {province_name} ({province_id}) ===")

    # Get crawler class and instantiate
    try:
        crawler_cls = get_crawler_class(province_id)
    except KeyError:
        logger.error(f"No crawler registered for {province_id}")
        return CrawlResult(
            province=province_name,
            province_id=province_id,
            status=CrawlStatus.FAILED,
            error_message=f"No crawler registered for {province_id}",
        )

    crawler = crawler_cls(province_config, settings, logger)

    # Crawl
    result = crawler.crawl()

    if result.status == CrawlStatus.FAILED:
        logger.error(f"[{province_name}] Crawl failed: {result.error_message}")
        db.save_crawl_log(result)
        return result

    # Diff with historical data
    existing_hashes = db.get_existing_hashes(province_name)
    records = classify_records(result.records, existing_hashes)

    # Count and persist
    for record in records:
        record.compute_hash()
        db.upsert_record(record)
    db.conn.commit()

    result.new_count = sum(1 for r in records if r.status == RecordStatus.NEW)
    result.updated_count = sum(1 for r in records if r.status == RecordStatus.UPDATED)
    result.unchanged_count = sum(1 for r in records if r.status == RecordStatus.UNCHANGED)

    # Structure alert
    if result.structure_alert:
        db.save_structure_alert(
            province_name,
            "structure_change",
            result.structure_alert_message,
        )

    db.save_crawl_log(result)
    logger.info(
        f"[{province_name}] Done: new={result.new_count}, "
        f"updated={result.updated_count}, unchanged={result.unchanged_count}"
    )
    return result


def main(argv: list[str] = None) -> int:
    """Entry point for the daily crawl run."""
    argv = argv or sys.argv[1:]
    dry_run = "--dry-run" in argv
    only_provinces = [a for a in argv if not a.startswith("-")]

    logger = setup_logger()
    logger.info(f"========== Daily crawl started: {today_str()} ==========")

    settings, provinces = load_config()
    if only_provinces:
        provinces = [p for p in provinces if p["id"] in only_provinces]
        logger.info(f"Running only: {[p['id'] for p in provinces]}")

    db_path = settings.get("database", {}).get("path", "data/mailbox.db")
    db = Database(str(PROJECT_ROOT / db_path))
    db.init_db()

    results: list[CrawlResult] = []
    for prov_config in provinces:
        result = run_single_province(prov_config, settings, db, logger)
        results.append(result)

    # Summary
    total_new = sum(r.new_count for r in results)
    total_updated = sum(r.updated_count for r in results)
    total_failed = sum(1 for r in results if r.status == CrawlStatus.FAILED)
    logger.info(
        f"========== Crawl complete: provinces={len(results)}, "
        f"new={total_new}, updated={total_updated}, failed={total_failed} =========="
    )

    if dry_run:
        logger.info("Dry run: skipping email report")
        db.close()
        return 0

    # Generate reports
    report_cfg = settings.get("report", {})
    output_dir = PROJECT_ROOT / report_cfg.get("output_dir", "output")
    output_dir.mkdir(parents=True, exist_ok=True)

    excel_name = report_cfg.get(
        "excel_template", "detail_{date}.xlsx"
    ).format(date=today_str())
    excel_path = str(output_dir / excel_name)

    logger.info("Generating Excel attachment...")
    generate_excel(results, excel_path)

    logger.info("Rendering HTML report...")
    template_path = str(PROJECT_ROOT / report_cfg.get(
        "html_template", "templates/daily_report.html.j2"
    ))
    html_body = render_html_report(results, template_path)

    # Send email
    logger.info("Sending email report...")
    try:
        subject_prefix = report_cfg.get("subject_prefix", "[厅长信箱监测日报]")
        subject = f"{subject_prefix} {today_str()}"
        send_email(html_body, excel_path, settings.get("email", {}), subject)
        logger.info("Email sent successfully")
    except Exception as exc:
        logger.error(f"Failed to send email: {exc}", exc_info=True)

    db.close()
    logger.info("All done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
