"""Configuracao de logging."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(log_dir: Path = Path("logs"), run_id: str = "-") -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("g1_lgpd_scraper")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    formatter = logging.Formatter(
        f"%(asctime)s [%(levelname)s] run={run_id} %(name)s: %(message)s"
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        log_dir / "scraper.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
