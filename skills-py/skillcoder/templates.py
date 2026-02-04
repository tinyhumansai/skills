"""
Code generation engine for skill-generator.

Generates skill.py, __init__.py, __main__.py, and manifest.json
for new AlphaHuman skills based on tool specifications.
"""

from __future__ import annotations

import json
from typing import Any


def _indent(text: str, level: int = 1) -> str:
  """Indent every line of text by the given level (4 spaces each)."""
  prefix = "    " * level
  return "\n".join(prefix + line if line.strip() else "" for line in text.split("\n"))


def _build_json_schema(params: list[dict[str, Any]]) -> dict[str, Any]:
  """Build a JSON Schema object from a list of parameter dicts.

  Each param dict has: name, type (string/number/integer/boolean/array/object),
  description, required (bool, default True).
  """
  properties: dict[str, Any] = {}
  required: list[str] = []

  for p in params:
    prop: dict[str, Any] = {
      "type": p.get("type", "string"),
      "description": p.get("description", ""),
    }
    properties[p["name"]] = prop
    if p.get("required", True):
      required.append(p["name"])

  schema: dict[str, Any] = {
    "type": "object",
    "properties": properties,
  }
  if required:
    schema["required"] = required
  return schema


def generate_skill_py(
  name: str,
  description: str,
  *,
  tools: list[dict[str, Any]] | None = None,
  include_tick: bool = False,
  tick_interval_ms: int = 60_000,
  include_transforms: bool = False,
  include_state: bool = False,
) -> str:
  """Generate a complete skill.py file.

  Args:
      name: Skill name (lowercase-hyphens).
      description: One-line skill description.
      tools: List of tool specs. Each has: name, description, parameters (list of param dicts).
      include_tick: Whether to include on_tick hook.
      tick_interval_ms: Tick interval in milliseconds.
      include_transforms: Whether to include on_before_message / on_after_response.
      include_state: Whether to include state persistence.
  """
  tools = tools or []
  lines: list[str] = []

  # Module docstring
  title = " ".join(w.capitalize() for w in name.split("-"))
  lines.append(f'"""{title} — AlphaHuman skill."""')
  lines.append("")
  lines.append("from __future__ import annotations")
  lines.append("")

  # Imports
  imports = ["SkillDefinition", "SkillContext", "SkillHooks"]
  if tools:
    imports.extend(["SkillTool", "ToolDefinition", "ToolResult"])
  lines.append("from dev.types.skill_types import (")
  for imp in imports:
    lines.append(f"    {imp},")
  lines.append(")")
  lines.append("")
  lines.append("")

  # --- Hooks ---
  # on_load
  lines.append("async def on_load(ctx: SkillContext) -> None:")
  lines.append(f'    ctx.log("{name} loaded")')
  if include_state:
    lines.append("    try:")
    lines.append("        import json as _json")
    lines.append('        raw = await ctx.read_data("state.json")')
    lines.append("        if raw:")
    lines.append("            ctx.set_state(_json.loads(raw))")
    lines.append("    except Exception:")
    lines.append("        pass")
  lines.append("")
  lines.append("")

  # on_session_start
  lines.append("async def on_session_start(ctx: SkillContext, session_id: str) -> None:")
  lines.append("    pass")
  lines.append("")
  lines.append("")

  # on_before_message / on_after_response
  if include_transforms:
    lines.append("async def on_before_message(ctx: SkillContext, message: str) -> str | None:")
    lines.append("    return None")
    lines.append("")
    lines.append("")
    lines.append("async def on_after_response(ctx: SkillContext, response: str) -> str | None:")
    lines.append("    return None")
    lines.append("")
    lines.append("")

  # on_tick
  if include_tick:
    lines.append("async def on_tick(ctx: SkillContext) -> None:")
    lines.append("    pass")
    lines.append("")
    lines.append("")

  # on_unload
  if include_state:
    lines.append("async def on_unload(ctx: SkillContext) -> None:")
    lines.append("    import json as _json")
    lines.append("    state = ctx.get_state()")
    lines.append("    if state:")
    lines.append('        await ctx.write_data("state.json", _json.dumps(state, indent=2))')
    lines.append("")
    lines.append("")

  # --- Tool functions ---
  for tool_spec in tools:
    fn_name = tool_spec["name"]
    tool_desc = tool_spec.get("description", "TODO: describe this tool")
    params = tool_spec.get("parameters", [])

    lines.append(f"async def _{fn_name}(args: dict) -> ToolResult:")
    lines.append(f'    """{tool_desc}"""')
    lines.append("    try:")

    # Extract parameters
    if params:
      for p in params:
        pname = p["name"]
        default = '""' if p.get("type", "string") == "string" else "None"
        lines.append(f'        {pname} = args.get("{pname}", {default})')
      lines.append('        return ToolResult(content="OK")')
    else:
      lines.append('        return ToolResult(content="OK")')

    lines.append("    except Exception as e:")
    lines.append('        return ToolResult(content=f"Error: {e}", is_error=True)')
    lines.append("")
    lines.append("")

  # --- Skill definition ---
  lines.append("skill = SkillDefinition(")
  lines.append(f'    name="{name}",')
  # Escape quotes in description
  safe_desc = description.replace('"', '\\"')
  lines.append(f'    description="{safe_desc}",')
  lines.append('    version="1.0.0",')

  # Hooks
  hooks_args = ["on_load=on_load", "on_session_start=on_session_start"]
  if include_transforms:
    hooks_args.append("on_before_message=on_before_message")
    hooks_args.append("on_after_response=on_after_response")
  if include_tick:
    hooks_args.append("on_tick=on_tick")
  if include_state:
    hooks_args.append("on_unload=on_unload")

  lines.append("    hooks=SkillHooks(")
  for arg in hooks_args:
    lines.append(f"        {arg},")
  lines.append("    ),")

  # Tools
  if tools:
    lines.append("    tools=[")
    for tool_spec in tools:
      fn_name = tool_spec["name"]
      tool_desc = tool_spec.get("description", "TODO: describe this tool")
      params = tool_spec.get("parameters", [])
      schema = _build_json_schema(params)

      lines.append("        SkillTool(")
      lines.append("            definition=ToolDefinition(")
      lines.append(f'                name="{fn_name}",')
      safe_tool_desc = tool_desc.replace('"', '\\"')
      lines.append(f'                description="{safe_tool_desc}",')
      schema_str = json.dumps(schema)
      lines.append(f"                parameters={schema_str},")
      lines.append("            ),")
      lines.append(f"            execute=_{fn_name},")
      lines.append("        ),")
    lines.append("    ],")

  if include_tick:
    lines.append(f"    tick_interval={tick_interval_ms},")

  lines.append(")")
  lines.append("")

  return "\n".join(lines)


def generate_main_py(name: str) -> str:
  """Generate __main__.py for a skill."""
  name.replace("-", "_")
  return f'''"""Entry point for the {name} skill subprocess."""

from __future__ import annotations

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="[%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)


def main() -> None:
    from dev.runtime.server import SkillServer
    from .skill import skill
    server = SkillServer(skill)
    server.start()


if __name__ == "__main__":
    main()
'''


def generate_init_py(name: str) -> str:
  """Generate __init__.py for a skill."""
  title = " ".join(w.capitalize() for w in name.split("-"))
  return f"# {title} — AlphaHuman skill.\n"


def generate_manifest_json(
  name: str,
  description: str,
  *,
  tick_interval_ms: int | None = None,
  dependencies: list[str] | None = None,
) -> str:
  """Generate manifest.json for a skill."""
  manifest: dict[str, Any] = {
    "id": name,
    "name": " ".join(w.capitalize() for w in name.split("-")),
    "version": "1.0.0",
    "description": description,
    "runtime": "python",
    "entry": "__main__.py",
  }
  if tick_interval_ms:
    manifest["tick_interval"] = tick_interval_ms
  manifest["dependencies"] = dependencies or ["pydantic>=2.0"]
  return json.dumps(manifest, indent=2) + "\n"
