"""CLI entry points."""

import argparse
import asyncio
import logging
import sys


def main():
    parser = argparse.ArgumentParser(prog="sentiment_api")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("api", help="Run API server")
    sub.add_parser("daemon", help="Run daemon (poll sources)")
    sub.add_parser("worker", help="Run worker (process queue)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    if args.cmd == "api":
        from sentiment_api.api.main import run
        run()
    elif args.cmd == "daemon":
        from sentiment_api.ingest.daemon import run_daemon
        asyncio.run(run_daemon())
    elif args.cmd == "worker":
        from sentiment_api.ingest.worker import run_worker
        asyncio.run(run_worker())


if __name__ == "__main__":
    main()
