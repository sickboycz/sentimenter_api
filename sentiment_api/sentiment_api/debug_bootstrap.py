"""Debug bootstrap: start debugpy listener when DEBUG_ATTACH=1 (e.g. Docker attach from Cursor)."""

import os


def run() -> None:
    """Start debugpy listener if DEBUG_ATTACH=1. Does not block unless DEBUG_WAIT=1."""
    if os.environ.get("DEBUG_ATTACH") != "1":
        return
    try:
        import debugpy
    except ImportError:
        import sys
        print("DEBUG_ATTACH=1 but debugpy not installed; skipping debug listener.", file=sys.stderr)
        return
    host = "0.0.0.0"
    try:
        port = int(os.environ.get("DEBUG_ATTACH_PORT", "5678"))
    except (TypeError, ValueError):
        port = 5678
    debugpy.listen((host, port))
    print(f"[debug] debugpy listening on {host}:{port} (attach from Cursor; set DEBUG_WAIT=1 to block until attached).")
    if os.environ.get("DEBUG_WAIT") == "1":
        debugpy.wait_for_client()
        print("[debug] debugger attached.")
