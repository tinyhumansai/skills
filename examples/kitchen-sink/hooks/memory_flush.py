"""
Memory flush hook — handle memory compaction events.
"""

from __future__ import annotations

from dev.types.skill_types import SkillContext


async def on_memory_flush(ctx: SkillContext) -> None:
  """Called when the memory system is about to compact/evict data.

  Use this to persist critical data before it's removed from memory.

  Demonstrates: memory.list, memory.read, write_data
  """
  # Example: save important memory entries to persistent storage
  all_keys = await ctx.memory.list()
  important_keys = [k for k in all_keys if k.startswith("kitchen-sink/")]

  for key in important_keys:
    content = await ctx.memory.read(key)
    if content:
      # Persist to data directory
      await ctx.write_data(f"backup/{key.replace('/', '_')}.json", content)

  ctx.log(f"kitchen-sink: flushed {len(important_keys)} memory entries to persistent storage")
