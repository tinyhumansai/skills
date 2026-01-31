"""
Entry point for the Telegram skill subprocess.

Run with: python -m skills.telegram
"""

from __future__ import annotations

import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="[%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)


def main() -> None:
    from .server import run_server
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
