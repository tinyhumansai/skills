from __future__ import annotations
from dev.types.skill_types import (
  SkillDefinition,
  SkillContext,
  SkillHooks,
  SkillTool,
  ToolDefinition,
  ToolResult,
)
import json
import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

"""Section: ---------------------------------------------------------------------------"""

# ---------------------------------------------------------------------------

skill = SkillDefinition(
  name="skill-generator",
  description="Meta-skill that creates, validates, tests, and scans new AlphaHuman skills on-the-fly.",
  version="1.0.0",
  options=TOOL_CATEGORY_OPTIONS,
  hooks=SkillHooks(
    on_load=_on_load,
    on_session_start=_on_session_start,
    on_before_message=_on_before_message,
    on_unload=_on_unload,
    on_status=_on_status,
  ),
  tools=_TOOLS,
)
