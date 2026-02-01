"""
Entity query tools — search the platform entity graph.
"""

from __future__ import annotations

from dev.types.skill_types import SkillContext, ToolResult


async def execute_find_entities(args: dict) -> ToolResult:
  """Query the platform entity graph.

  Demonstrates: entities.search, entities.get_by_tag
  """
  ctx: SkillContext = args.pop("__context__")
  query = args.get("query", "")
  entity_type = args.get("type")

  if query.startswith("#"):
    # Tag-based search
    tag = query.lstrip("#")
    results = await ctx.entities.get_by_tag(tag, type=entity_type)
  else:
    # Free-text search
    results = await ctx.entities.search(query)

  if not results:
    return ToolResult(content="No entities found.")

  lines = []
  for e in results[:10]:
    tags = ", ".join(e.tags) if e.tags else "none"
    lines.append(f"- [{e.type}] **{e.name}** (id={e.id}, tags={tags})")

  return ToolResult(content=f"Entities ({len(results)}):\n" + "\n".join(lines))
