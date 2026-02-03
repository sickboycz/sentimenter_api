#!/usr/bin/env python3
"""
Verify debug attach setup: port 5678 listening in container, API responds.
Run from sentiment_api/ with debug stack up:
  docker compose -f docker-compose.yml -f docker-compose.debug.yml up -d
  python scripts/verify_debug_attach.py
"""
import os
import subprocess
import sys
import urllib.request

COMPOSE_ARGS = ["-f", "docker-compose.yml", "-f", "docker-compose.debug.yml"]
API_SERVICE = "api"
HEALTH_URL = "http://localhost:8080/v1/health"
DEBUG_PORT = 5678


def run(cmd: list[str], capture: bool = True) -> tuple[int, str]:
    r = subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        timeout=30,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
    out = (r.stdout or "") + (r.stderr or "")
    return r.returncode, out


def main() -> int:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.isdir(os.path.join(root, "sentiment_api")):
        print("FAIL: Run from sentiment_api/ (parent of scripts/).")
        return 1

    # 1) Port 5678 listening inside container (Python socket check; no ss/netstat required)
    code, out = run(
        ["docker", "compose"] + COMPOSE_ARGS + [
            "exec", "-T", API_SERVICE,
            "python", "-c",
            "import socket; s=socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(2); s.connect(('127.0.0.1', 5678)); s.close()",
        ]
    )
    if code != 0:
        print("FAIL: Port 5678 is not listening inside the api container.")
        print("  Ensure you started with: docker compose -f docker-compose.yml -f docker-compose.debug.yml up -d")
        return 1
    print("PASS: Port 5678 is listening in container.")

    # 2) API health
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=5) as r:
            if r.getcode() != 200:
                print(f"FAIL: {HEALTH_URL} returned {r.getcode()}.")
                return 1
    except Exception as e:
        print(f"FAIL: {HEALTH_URL} request failed: {e}")
        return 1
    print("PASS: API health endpoint responded.")

    print("All checks passed. Attach from Cursor to 127.0.0.1:5678.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
