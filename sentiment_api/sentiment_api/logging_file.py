"""Optional file logging to /data/logs/<service>.log for admin log viewer. Also logs to stdout so docker logs works."""

import logging
import sys
from pathlib import Path

LOG_DIR = Path("/data/logs")
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def add_file_handler(service: str) -> None:
    """Add FileHandler + StreamHandler to sentiment_api logger so docker logs and /data/logs/<service>.log both get output."""
    root = logging.getLogger("sentiment_api")
    root.setLevel(logging.DEBUG)
    formatter = logging.Formatter(LOG_FORMAT)
    # Stdout so docker logs shows logs
    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(formatter)
    stream.setLevel(logging.DEBUG)
    root.addHandler(stream)
    # File if /data/logs exists
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        return
    log_file = LOG_DIR / f"{service}.log"
    try:
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(formatter)
        handler.setLevel(logging.DEBUG)
        root.addHandler(handler)
    except OSError:
        pass
