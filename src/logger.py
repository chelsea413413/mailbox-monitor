"""日志配置：同时输出到文件和控制台，按日期轮转。"""
from __future__ import annotations

import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from .models import today_str


_configured = False


def setup_logger(log_dir: str = "logs", level: str = "INFO") -> logging.Logger:
    """初始化全局 logger，返回可复用的 Logger 实例。"""
    global _configured
    logger = logging.getLogger("mailbox_monitor")

    if _configured:
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # 文件 handler：按天轮转，保留 30 天
    file_handler = TimedRotatingFileHandler(
        log_path / f"crawl_{today_str()}.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    # 控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    )

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    _configured = True
    return logger


def get_logger(name: str = "mailbox_monitor") -> logging.Logger:
    """获取子 logger。"""
    return logging.getLogger(name)
