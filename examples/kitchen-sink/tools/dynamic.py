"""
Dynamic tool registration — register tools at runtime.
"""

from __future__ import annotations

from dev.types.skill_types import SkillContext, SkillTool, ToolDefinition, ToolResult


async def execute_dynamic_tool(args: dict) -> ToolResult:
  """Example dynamic tool that can be registered at runtime."""
  ctx: SkillContext = args.pop("__context__")
  protocol = args.get("protocol", "")

  return ToolResult(content=f"Advanced analytics for {protocol} (dynamic tool example)")


async def _register_dynamic_tools(ctx: SkillContext) -> None:
  """Register dynamic tools based on configuration or feature flags."""
  state = ctx.get_state() or {}
  config = state.get("config", {})

  # Example: register an extra tool only for advanced/degen users
  if config.get("experience") in ("advanced", "degen"):
    ctx.tools.register(
      SkillTool(
        definition=ToolDefinition(
          name="advanced_analytics",
          description="Run advanced on-chain analytics (advanced users only).",
          parameters={
            "type": "object",
            "properties": {
              "protocol": {
                "type": "string",
                "description": "Protocol to analyze",
              },
            },
            "required": ["protocol"],
          },
        ),
        execute=execute_dynamic_tool,
      )
    )
    ctx.log("kitchen-sink: registered advanced_analytics tool")
