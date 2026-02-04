"""
Skill Coder - Meta-skill that creates, validates, tests, and scans new AlphaHuman skills on-the-fly.
"""

from pathlib import Path

# Repo root: skills/skill-generator/../../ => skills repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SKILLS_DIR = _REPO_ROOT / "skills"

# Try to import skill definition from skill_section.py
# If that fails (e.g., due to missing dependencies or incomplete definition),
# create a minimal skill definition for validation/catalog purposes
try:
  from .skill_section import skill
except (ImportError, NameError, AttributeError):
  # Fallback: create minimal skill definition
  from dev.types.skill_types import SkillDefinition

  skill = SkillDefinition(
    name="skillcoder",
    description="A skill that makes new skills on it's own.",
    version="1.0.0",
    tools=[],
  )
