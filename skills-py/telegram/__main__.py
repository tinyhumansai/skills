"""
Entry point for the Telegram skill subprocess.

Run with: python -m skills.telegram          (SkillServer JSON-RPC mode)
          python -m skills.telegram --mcp    (MCP stdio server mode)
"""

from __future__ import annotations

import logging
import sys

logging.basicConfig(
  level=logging.INFO,
  format="[%(name)s] %(levelname)s: %(message)s",
  stream=sys.stderr,
)


def main() -> None:
  if "--mcp" in sys.argv:
    import asyncio

    from .server import run_server

    asyncio.run(run_server())
  else:
    from dev.runtime.server import SkillServer

    from .skill import skill

    server = SkillServer(skill)
    server.start()


if __name__ == "__main__":
  main()
