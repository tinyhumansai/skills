"""
Browser skill entry point.

Runs the skill server using the standard runtime.
"""

from dev.runtime.server import SkillServer

from .skill import skill

if __name__ == "__main__":
  server = SkillServer(skill)
  server.start()
