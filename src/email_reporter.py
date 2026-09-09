"""Email reporter: renders HTML report and sends via SMTP with Excel attachment."""
from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .models import CrawlResult, CrawlStatus, today_str


def _expand_env(value: str) -> str:
    """Expand  references from environment variables."""
    if not value:
        return value
    return os.path.expandvars(value)


def render_html_report(
    results: list[CrawlResult],
    template_path: str = "templates/daily_report.html.j2",
) -> str:
    """Render the HTML email body from crawl results using Jinja2."""
    template_dir = str(Path(template_path).parent)
    template_name = Path(template_path).name

    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html", "j2"]),
    )
    template = env.get_template(template_name)

    structure_alerts = []
    for r in results:
        if r.structure_alert:
            structure_alerts.append({
                "province": r.province,
                "message": r.structure_alert_message,
            })

    total_new = sum(r.new_count for r in results)
    total_updated = sum(r.updated_count for r in results)
    total_success = sum(
        1 for r in results
        if r.status in (CrawlStatus.SUCCESS, CrawlStatus.NO_NEW, CrawlStatus.PARTIAL)
    )
    total_failed = sum(1 for r in results if r.status == CrawlStatus.FAILED)

    return template.render(
        report_date=today_str(),
        results=results,
        total_new=total_new,
        total_updated=total_updated,
        total_success=total_success,
        total_failed=total_failed,
        structure_alerts=structure_alerts,
    )


def send_email(
    html_body: str,
    excel_path: Optional[str],
    email_config: dict,
    subject: str = None,
) -> None:
    """Send the daily report email with optional Excel attachment."""
    smtp_host = _expand_env(email_config.get("smtp_host", ""))
    smtp_port = int(email_config.get("smtp_port", 465))
    smtp_user = _expand_env(email_config.get("smtp_user", ""))
    smtp_password = _expand_env(email_config.get("smtp_password", ""))
    from_addr = _expand_env(email_config.get("from_addr", smtp_user))
    to_addrs_raw = _expand_env(email_config.get("to_addrs", ""))
    use_ssl = email_config.get("use_ssl", True)
    to_addrs = [a.strip() for a in to_addrs_raw.split(",") if a.strip()]

    if not smtp_host or not to_addrs:
        raise ValueError("SMTP host and recipient addresses are required")

    subj = subject or f"[厅长信箱监测日报] {today_str()}"
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subj
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs)

    html_part = MIMEText(html_body, "html", "utf-8")
    msg.attach(html_part)

    if excel_path and Path(excel_path).exists():
        with open(excel_path, "rb") as f:
            attachment = MIMEBase("application", "octet-stream")
            attachment.set_payload(f.read())
        encoders.encode_base64(attachment)
        attachment.add_header(
            "Content-Disposition",
            f'attachment; filename="{Path(excel_path).name}"',
        )
        msg.attach(attachment)

    if use_ssl:
        server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30)
    else:
        server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
        server.starttls()

    try:
        if smtp_user and smtp_password:
            server.login(smtp_user, smtp_password)
        server.sendmail(from_addr, to_addrs, msg.as_string())
    finally:
        server.quit()
