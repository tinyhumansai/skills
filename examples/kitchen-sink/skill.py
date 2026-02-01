"""
Kitchen-sink SkillDefinition — comprehensive example demonstrating all capabilities.

Usage:
    from examples.kitchen_sink.skill import skill
"""

from __future__ import annotations

from dev.types.skill_types import (
  SkillDefinition,
  SkillHooks,
  SkillTool,
  ToolDefinition,
)

# Use absolute imports that work when skill.py is executed directly
# The runtime adds the repo root to sys.path, so we can import from the skill directory
import sys
from pathlib import Path

# Add current directory to path for local imports
_skill_dir = Path(__file__).parent
if str(_skill_dir) not in sys.path:
  sys.path.insert(0, str(_skill_dir))

from hooks import (
  on_load,
  on_unload,
  on_session_start,
  on_session_end,
  on_tick,
  on_before_message,
  on_after_response,
  on_memory_flush,
  on_status,
)
from setup import on_setup_start, on_setup_submit, on_setup_cancel
from tools import (
  execute_add_note,
  execute_get_note,
  execute_list_notes,
  execute_search_memory,
  execute_save_memory,
  execute_find_entities,
  execute_get_session_info,
)


def _build_tools() -> list[SkillTool]:
  """Build SkillTool list from tool implementations."""
  return [
    SkillTool(
      definition=ToolDefinition(
        name="add_note",
        description="Save a note to the skill's persistent data directory.",
        parameters={
          "type": "object",
          "properties": {
            "title": {
              "type": "string",
              "description": "Note title",
            },
            "body": {
              "type": "string",
              "description": "Note content",
            },
          },
          "required": ["title"],
        },
      ),
      execute=execute_add_note,
    ),
    SkillTool(
      definition=ToolDefinition(
        name="get_note",
        description="Retrieve a note by its ID.",
        parameters={
          "type": "object",
          "properties": {
            "note_id": {
              "type": "string",
              "description": "Note ID (e.g., 'note_1')",
            },
          },
          "required": ["note_id"],
        },
      ),
      execute=execute_get_note,
    ),
    SkillTool(
      definition=ToolDefinition(
        name="list_notes",
        description="List all saved notes.",
        parameters={
          "type": "object",
          "properties": {},
        },
      ),
      execute=execute_list_notes,
    ),
    SkillTool(
      definition=ToolDefinition(
        name="search_memory",
        description="Search the shared memory system.",
        parameters={
          "type": "object",
          "properties": {
            "query": {
              "type": "string",
              "description": "Search query",
            },
          },
          "required": ["query"],
        },
      ),
      execute=execute_search_memory,
    ),
    SkillTool(
      definition=ToolDefinition(
        name="save_memory",
        description="Write to the shared memory system.",
        parameters={
          "type": "object",
          "properties": {
            "name": {
              "type": "string",
              "description": "Memory entry name",
            },
            "content": {
              "type": "string",
              "description": "Memory content",
            },
          },
          "required": ["name", "content"],
        },
      ),
      execute=execute_save_memory,
    ),
    SkillTool(
      definition=ToolDefinition(
        name="find_entities",
        description="Query the platform entity graph.",
        parameters={
          "type": "object",
          "properties": {
            "query": {
              "type": "string",
              "description": "Search query (use #tag for tag-based search)",
            },
            "type": {
              "type": "string",
              "description": "Filter by entity type (optional)",
            },
          },
          "required": ["query"],
        },
      ),
      execute=execute_find_entities,
    ),
    SkillTool(
      definition=ToolDefinition(
        name="get_session_info",
        description="Return current session information.",
        parameters={
          "type": "object",
          "properties": {},
        },
      ),
      execute=execute_get_session_info,
    ),
  ]


skill = SkillDefinition(
  name="kitchen-sink",
  description=(
    "Comprehensive example skill demonstrating every capability: "
    "lifecycle hooks, tools, setup flow, state, memory, entities, "
    "events, and periodic tasks."
  ),
  version="1.0.0",
  tools=_build_tools(),
  tick_interval=60_000,  # 60 seconds, in milliseconds
  has_setup=True,
  hooks=SkillHooks(
    on_load=on_load,
    on_unload=on_unload,
    on_session_start=on_session_start,
    on_session_end=on_session_end,
    on_before_message=on_before_message,
    on_after_response=on_after_response,
    on_memory_flush=on_memory_flush,
    on_tick=on_tick,
    on_status=on_status,
    on_setup_start=on_setup_start,
    on_setup_submit=on_setup_submit,
    on_setup_cancel=on_setup_cancel,
  ),
)
