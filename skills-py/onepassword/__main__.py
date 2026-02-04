"""
1Password skill entry point.
"""

from __future__ import annotations

from dev.runtime.server import run_skill_server

from .skill import skill

if __name__ == "__main__":
  run_skill_server(skill)
