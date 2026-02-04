"""
Entry point for the Wallet skill subprocess.

Run with: python -m skills.wallet
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
  from dev.runtime.server import SkillServer

  from .skill import skill

  server = SkillServer(skill)
  server.start()


if __name__ == "__main__":
  main()
