"""Optional file logging to /data/logs/<service>.log for admin log viewer."""

import logging
from pathlib import Path

LOG_DIR = Path("/data/logs")
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def add_file_handler(service: str) -> None:
    """Add a FileHandler to sentiment_api logger writing to /data/logs/<service>.log if dir exists."""
    if not LOG_DIR.is_dir():
        return
    log_file = LOG_DIR / f"{service}.log"
    try:
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        handler.setLevel(logging.DEBUG)
        root = logging.getLogger("sentiment_api")
        root.setLevel(logging.DEBUG)
        root.addHandler(handler)
    except OSError:
        pass
