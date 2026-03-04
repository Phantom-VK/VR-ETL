"""Project-wide logging configuration."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

# Determine project root (two levels up from this file: src/utils/logger.py)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Log directory: logs/<dd_mm_YYYY_HH:MM>/
timestamp_dir = datetime.now().strftime("%d_%m_%Y_%H:%M")
logs_path = PROJECT_ROOT / "logs" / timestamp_dir
logs_path.mkdir(parents=True, exist_ok=True)

# Log file name: <dd_mm_YYYY_HH:MM:SS>.log
log_file = f"{datetime.now().strftime('%d_%m_%Y_%H:%M:%S')}.log"
LOG_FILE_PATH = logs_path / log_file


def _configure_logging() -> None:
    """Configure root logging once."""
    if logging.getLogger().handlers:
        return  # already configured
    logging.basicConfig(
        handlers=[
            logging.FileHandler(LOG_FILE_PATH),
            logging.StreamHandler(),
        ],
        format="[ %(asctime)s ] %(lineno)d %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )


_configure_logging()

logger = logging.getLogger("vr_etl")

__all__ = ["logger", "PROJECT_ROOT", "LOG_FILE_PATH"]
