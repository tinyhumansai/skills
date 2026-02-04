"""
Entry point for the Otter.ai skill subprocess.

Run with: python -m skills.otter          (SkillServer JSON-RPC mode)
          python -m skills.otter --mcp    (MCP stdio server mode)
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
    # MCP mode not implemented for Otter — fall through to SkillServer
    from dev.runtime.server import SkillServer

    from .skill import skill

    server = SkillServer(skill)
    server.start()
  else:
    from dev.runtime.server import SkillServer

    from .skill import skill

    server = SkillServer(skill)
    server.start()


if __name__ == "__main__":
  main()
