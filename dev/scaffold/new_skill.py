"""
Interactive skill scaffolder.

Creates a new skill directory with a skill.py from the user's choices.

Usage:
    python -m dev.scaffold.new_skill [skill-name]

If skill-name is provided, skips the name prompt.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Console helpers
# ---------------------------------------------------------------------------


def bold(s: str) -> str:
    return f"\033[1m{s}\033[0m"


def green(s: str) -> str:
    return f"\033[32m{s}\033[0m"


def dim(s: str) -> str:
    return f"\033[2m{s}\033[0m"


NAME_PATTERN = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


# ---------------------------------------------------------------------------
# Prompt helpers
# ---------------------------------------------------------------------------


def ask(question: str) -> str:
    return input(question).strip()


def ask_yes_no(question: str, default_yes: bool = True) -> bool:
    hint = "[Y/n]" if default_yes else "[y/N]"
    answer = input(f"{question} {hint} ").strip().lower()
    if answer == "":
        return default_yes
    return answer in ("y", "yes")


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------


def generate_skill_py(
    name: str,
    description: str,
    *,
    tools: bool = False,
    tick: bool = False,
    transforms: bool = False,
    state: bool = False,
) -> str:
    """Generate the content of a skill.py file."""
    parts: list[str] = []

    parts.append('"""')
    title = " ".join(w.capitalize() for w in name.split("-"))
    parts.append(f"{title} — AlphaHuman skill.")
    parts.append('"""')
    parts.append("")
    parts.append("from __future__ import annotations")
    parts.append("")
    parts.append("from dev.types.skill_types import (")
    parts.append("    SkillDefinition,")
    parts.append("    SkillContext,")
    parts.append("    SkillHooks,")
    if tools:
        parts.append("    SkillTool,")
        parts.append("    ToolDefinition,")
        parts.append("    ToolResult,")
    parts.append(")")
    parts.append("")
    parts.append("")

    # --- Hooks ---
    parts.append("async def on_load(ctx: SkillContext) -> None:")
    parts.append(f'    ctx.log("{name} loaded")')
    if state:
        parts.append("    # Load persisted state")
        parts.append("    try:")
        parts.append("        import json")
        parts.append('        data = await ctx.read_data("state.json")')
        parts.append("        ctx.set_state(json.loads(data))")
        parts.append("    except FileNotFoundError:")
        parts.append("        pass  # No previous state")
    parts.append("")
    parts.append("")

    parts.append("async def on_session_start(ctx: SkillContext, session_id: str) -> None:")
    parts.append("    # React to new chat sessions")
    parts.append("    pass")
    parts.append("")
    parts.append("")

    if transforms:
        parts.append("async def on_before_message(ctx: SkillContext, message: str) -> str | None:")
        parts.append("    # Transform user message before AI processes it")
        parts.append("    # Return a string to transform, or None to pass through")
        parts.append("    return None")
        parts.append("")
        parts.append("")
        parts.append("async def on_after_response(ctx: SkillContext, response: str) -> str | None:")
        parts.append("    # Transform AI response before it's shown to user")
        parts.append("    # Return a string to transform, or None to pass through")
        parts.append("    return None")
        parts.append("")
        parts.append("")

    if tick:
        parts.append("async def on_tick(ctx: SkillContext) -> None:")
        parts.append("    # Periodic task — runs every tick_interval ms")
        parts.append("    pass")
        parts.append("")
        parts.append("")

    if state:
        parts.append("async def on_unload(ctx: SkillContext) -> None:")
        parts.append("    # Persist state on shutdown")
        parts.append("    import json")
        parts.append("    state = ctx.get_state()")
        parts.append('    await ctx.write_data("state.json", json.dumps(state, indent=2))')
        parts.append("")
        parts.append("")

    # --- Tools ---
    if tools:
        tool_fn_name = name.replace("-", "_") + "_action"
        parts.append(f"async def {tool_fn_name}(args: dict) -> ToolResult:")
        parts.append('    input_val = args.get("input", "")')
        parts.append('    return ToolResult(content=f"Result: {input_val}")')
        parts.append("")
        parts.append("")

    # --- Skill definition ---
    parts.append("skill = SkillDefinition(")
    parts.append(f'    name="{name}",')
    parts.append(f'    description="{description}",')
    parts.append('    version="1.0.0",')

    # Hooks
    hooks_args: list[str] = ["on_load=on_load", "on_session_start=on_session_start"]
    if transforms:
        hooks_args.extend(
            ["on_before_message=on_before_message", "on_after_response=on_after_response"]
        )
    if tick:
        hooks_args.append("on_tick=on_tick")
    if state:
        hooks_args.append("on_unload=on_unload")
    parts.append(f"    hooks=SkillHooks(")
    for arg in hooks_args:
        parts.append(f"        {arg},")
    parts.append("    ),")

    # Tools
    if tools:
        tool_fn_name = name.replace("-", "_") + "_action"
        parts.append("    tools=[")
        parts.append("        SkillTool(")
        parts.append("            definition=ToolDefinition(")
        parts.append(f'                name="{tool_fn_name}",')
        parts.append('                description="TODO: describe what this tool does",')
        parts.append("                parameters={")
        parts.append('                    "type": "object",')
        parts.append('                    "properties": {')
        parts.append(
            '                        "input": {"type": "string", "description": "TODO: describe parameter"},'
        )
        parts.append("                    },")
        parts.append('                    "required": ["input"],')
        parts.append("                },")
        parts.append("            ),")
        parts.append(f"            execute={tool_fn_name},")
        parts.append("        ),")
        parts.append("    ],")

    if tick:
        parts.append("    tick_interval=60_000,  # every minute")

    parts.append(")")
    parts.append("")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    cli_name = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else None
    dev_dir = Path(__file__).resolve().parent.parent
    root_dir = dev_dir.parent
    skills_dir = root_dir / "skills"

    print()
    print(bold("AlphaHuman Skill Scaffolder"))
    print()

    try:
        # --- Skill name ---
        name = cli_name
        if not name:
            name = ask("  Skill name (lowercase-hyphens): ")
        if not NAME_PATTERN.match(name):
            print(f'  Error: "{name}" is not a valid skill name.', file=sys.stderr)
            print('  Use lowercase letters and hyphens (e.g., "my-skill").', file=sys.stderr)
            sys.exit(1)

        target_dir = skills_dir / name
        if target_dir.exists():
            print(f'  Error: Directory "{name}" already exists in skills/.', file=sys.stderr)
            sys.exit(1)

        # --- Description ---
        description = ask("  Description (one sentence): ")
        if not description:
            print("  Error: Description is required.", file=sys.stderr)
            sys.exit(1)

        # --- Features ---
        wants_tools = ask_yes_no("  Include custom tools?")
        wants_tick = ask_yes_no("  Include periodic tick (on_tick)?", default_yes=False)
        wants_transforms = ask_yes_no("  Include message transforms?", default_yes=False)
        wants_state = ask_yes_no("  Include persistent state?", default_yes=False)

        # --- Create files ---
        print()
        print(f"  Creating {bold(name)}...")

        target_dir.mkdir(parents=True, exist_ok=True)

        skill_py_content = generate_skill_py(
            name,
            description,
            tools=wants_tools,
            tick=wants_tick,
            transforms=wants_transforms,
            state=wants_state,
        )
        (target_dir / "skill.py").write_text(skill_py_content, encoding="utf-8")
        print(f"  {green(chr(0x2713))} skill.py")

        print()
        print(green("  Done!"))
        print()
        print("  Next steps:")
        print(f"    1. Edit {dim(f'skills/{name}/skill.py')} — implement hooks/tools")
        print(f"    2. Test: {dim(f'python -m dev.harness.runner skills/{name}')}")
        print(f"    3. Validate: {dim('python -m dev.validate.validator')}")
        print(f"    4. Submit a pull request")
        print()

    except (KeyboardInterrupt, EOFError):
        print("\n  Cancelled.")
        sys.exit(1)


if __name__ == "__main__":
    main()
