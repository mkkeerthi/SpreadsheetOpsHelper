from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"


def _unique_path(candidate: Path) -> Path:
    if not candidate.exists():
        return candidate
    counter = 1
    while True:
        alternative = candidate.with_name(f"{candidate.stem}_{counter}{candidate.suffix}")
        if not alternative.exists():
            return alternative
        counter += 1


def get_run_logger() -> tuple[logging.Logger, Path]:
    """Create a fresh timestamped log file under logs/ and return its logger."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = _unique_path(LOGS_DIR / f"copy_{stamp}.log")

    logger = logging.getLogger(f"numbers_helper.{log_path.stem}")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(handler)

    return logger, log_path


def close_run_logger(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)
