"""
Note management tools — add, get, and list notes.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from dev.types.skill_types import SkillContext, ToolResult


def _now() -> str:
  """Get current timestamp."""
  return datetime.now(timezone.utc).isoformat()


async def execute_add_note(args: dict) -> ToolResult:
  """Save a note to the skill's persistent data directory.

  Demonstrates: write_data, get_state, set_state, emit_event
  """
  ctx: SkillContext = args.pop("__context__")
  title = args.get("title", "Untitled")
  body = args.get("body", "")

  # Read existing notes index from persistent state
  state = ctx.get_state() or {}
  notes: list[dict] = state.get("notes_index", [])

  note_id = f"note_{len(notes) + 1}"
  note = {
    "id": note_id,
    "title": title,
    "body": body,
    "created_at": _now(),
  }

  # Persist the note content as a file in data_dir
  await ctx.write_data(f"{note_id}.json", json.dumps(note, indent=2))

  # Update the index in skill state
  notes.append({"id": note_id, "title": title})
  ctx.set_state({"notes_index": notes})

  # Emit an event so intelligence rules can react
  ctx.emit_event("note_created", {"note_id": note_id, "title": title})

  return ToolResult(content=f"Note '{title}' saved as {note_id}.")


async def execute_get_note(args: dict) -> ToolResult:
  """Retrieve a note by its ID.

  Demonstrates: read_data, error handling
  """
  ctx: SkillContext = args.pop("__context__")
  note_id = args.get("note_id", "")

  try:
    raw = await ctx.read_data(f"{note_id}.json")
    note = json.loads(raw)
    return ToolResult(
      content=f"**{note['title']}**\n\n{note['body']}\n\n_Created: {note['created_at']}_"
    )
  except Exception as e:
    return ToolResult(content=f"Note not found: {e}", is_error=True)


async def execute_list_notes(args: dict) -> ToolResult:
  """List all saved notes.

  Demonstrates: get_state
  """
  ctx: SkillContext = args.pop("__context__")
  state = ctx.get_state() or {}
  notes = state.get("notes_index", [])

  if not notes:
    return ToolResult(content="No notes saved yet.")

  lines = [f"- **{n['id']}**: {n['title']}" for n in notes]
  return ToolResult(content=f"Notes ({len(notes)}):\n" + "\n".join(lines))
