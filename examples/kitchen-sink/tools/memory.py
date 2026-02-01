"""
Memory management tools — search and save to shared memory.
"""

from __future__ import annotations

from dev.types.skill_types import SkillContext, ToolResult


async def execute_search_memory(args: dict) -> ToolResult:
  """Search the shared memory system.

  Demonstrates: memory.search
  """
  ctx: SkillContext = args.pop("__context__")
  query = args.get("query", "")

  results = await ctx.memory.search(query)

  if not results:
    return ToolResult(content=f"No memory results for '{query}'.")

  lines = []
  for r in results[:10]:
    name = r.get("name", "unknown")
    snippet = r.get("content", "")[:120]
    lines.append(f"- **{name}**: {snippet}")

  return ToolResult(content=f"Memory search results ({len(results)}):\n" + "\n".join(lines))


async def execute_save_memory(args: dict) -> ToolResult:
  """Write to the shared memory system.

  Demonstrates: memory.write
  """
  ctx: SkillContext = args.pop("__context__")
  name = args.get("name", "")
  content = args.get("content", "")

  await ctx.memory.write(name, content)
  return ToolResult(content=f"Memory '{name}' saved.")
