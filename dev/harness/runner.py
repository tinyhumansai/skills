"""
Skill Test Runner

Loads a skill directory, validates its structure, and exercises all
lifecycle hooks and tools against a mock context.

Usage:
    python -m dev.harness.runner <skill-dir> [--verbose]

Examples:
    python -m dev.harness.runner skills/price-tracker
    python -m dev.harness.runner skills/price-tracker --verbose
"""

from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path
from typing import Any

from dev.harness.mock_context import MockContextOptions, create_mock_context
from dev.types.skill_types import SkillDefinition
from dev.types.setup_types import SetupStep, SetupResult

# ---------------------------------------------------------------------------
# Console helpers
# ---------------------------------------------------------------------------

PASS = "\033[32m\u2713\033[0m"
FAIL = "\033[31m\u2717\033[0m"
WARN = "\033[33m!\033[0m"


def bold(s: str) -> str:
  return f"\033[1m{s}\033[0m"


def dim(s: str) -> str:
  return f"\033[2m{s}\033[0m"


pass_count = 0
fail_count = 0
warn_count = 0


def _pass(msg: str) -> None:
  global pass_count
  pass_count += 1
  print(f"  {PASS} {msg}")


def _fail(msg: str) -> None:
  global fail_count
  fail_count += 1
  print(f"  {FAIL} {msg}")


def _warn(msg: str) -> None:
  global warn_count
  warn_count += 1
  print(f"  {WARN} {msg}")


def _info(msg: str) -> None:
  print(f"  {dim(msg)}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def generate_arg(schema: dict[str, Any]) -> Any:
  """Generate a dummy value for a JSON Schema property."""
  typ = schema.get("type", "")
  if typ == "string":
    if "enum" in schema:
      return schema["enum"][0]
    return "test-value"
  if typ in ("number", "integer"):
    return 42
  if typ == "boolean":
    return True
  if typ == "array":
    items = schema.get("items")
    return [generate_arg(items)] if isinstance(items, dict) else []
  if typ == "object":
    props = schema.get("properties", {})
    return {k: generate_arg(v) for k, v in props.items()}
  return None


def load_skill_module(skill_py_path: Path) -> SkillDefinition:
  """Dynamically import a skill.py and return its `skill` object."""
  spec = importlib.util.spec_from_file_location("_skill_module", skill_py_path)
  if spec is None or spec.loader is None:
    raise ImportError(f"Cannot load module from {skill_py_path}")
  module = importlib.util.module_from_spec(spec)
  # Add parent directories to sys.path so relative imports work
  repo_root = skill_py_path.parent.parent.parent
  if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
  spec.loader.exec_module(module)
  skill_obj = getattr(module, "skill", None)
  if skill_obj is None:
    raise ImportError("skill.py must export a `skill` variable")
  if isinstance(skill_obj, SkillDefinition):
    return skill_obj
  # Try to coerce dict-like objects
  return SkillDefinition.model_validate(skill_obj)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def _run(skill_dir: str, verbose: bool) -> int:
  global pass_count, fail_count, warn_count
  pass_count = fail_count = warn_count = 0

  abs_dir = Path(skill_dir).resolve()
  skill_name = abs_dir.name

  print()
  print(bold(f"Testing skill: {skill_name}"))
  print(dim(f"  Directory: {abs_dir}"))
  print()

  # -------------------------------------------------------------------
  # 1. Check skill.py exists
  # -------------------------------------------------------------------
  print(bold("skill.py"))
  skill_py_path = abs_dir / "skill.py"

  if not skill_py_path.exists():
    _fail("skill.py not found")
    print()
    _print_summary()
    return 1

  _pass("skill.py exists")

  skill: SkillDefinition
  try:
    skill = load_skill_module(skill_py_path)
    _pass("Has `skill` export")
  except Exception as exc:
    _fail(f"Failed to import skill.py: {exc}")
    if verbose:
      import traceback

      traceback.print_exc()
    _print_summary()
    return 1

  # Validate structure
  if skill.name:
    _pass(f'name: "{skill.name}"')
  else:
    _fail("Missing name")

  if skill.description:
    _pass(f'description: "{skill.description}"')
  else:
    _fail("Missing description")

  if skill.version:
    import re

    if re.match(r"^\d+\.\d+\.\d+", skill.version):
      _pass(f"version: {skill.version}")
    else:
      _warn(f'version "{skill.version}" is not semver')
  else:
    _fail("Missing version")

  if skill.name != skill_name:
    _warn(f'Skill name "{skill.name}" does not match directory "{skill_name}"')

  if skill.tick_interval is not None:
    if skill.tick_interval >= 1000:
      _pass(f"tick_interval: {skill.tick_interval}ms")
    else:
      _fail(f"tick_interval {skill.tick_interval}ms is below minimum (1000ms)")

  print()

  # -------------------------------------------------------------------
  # 2. Run lifecycle hooks
  # -------------------------------------------------------------------
  print(bold("Lifecycle Hooks"))
  ctx, inspect = create_mock_context(
    MockContextOptions(
      initial_data={},
      session_id="runner-session-001",
    )
  )

  hooks_obj = skill.hooks
  hook_order: list[tuple[str, Any]] = [
    ("on_load", lambda: hooks_obj.on_load(ctx) if hooks_obj and hooks_obj.on_load else None),
    (
      "on_session_start",
      lambda: hooks_obj.on_session_start(ctx, "runner-session-001")
      if hooks_obj and hooks_obj.on_session_start
      else None,
    ),
    (
      "on_before_message",
      lambda: hooks_obj.on_before_message(ctx, "What is the price of ETH?")
      if hooks_obj and hooks_obj.on_before_message
      else None,
    ),
    (
      "on_after_response",
      lambda: hooks_obj.on_after_response(ctx, "ETH is currently $3,400.")
      if hooks_obj and hooks_obj.on_after_response
      else None,
    ),
    ("on_tick", lambda: hooks_obj.on_tick(ctx) if hooks_obj and hooks_obj.on_tick else None),
    (
      "on_memory_flush",
      lambda: hooks_obj.on_memory_flush(ctx) if hooks_obj and hooks_obj.on_memory_flush else None,
    ),
    (
      "on_session_end",
      lambda: hooks_obj.on_session_end(ctx, "runner-session-001")
      if hooks_obj and hooks_obj.on_session_end
      else None,
    ),
    (
      "on_unload",
      lambda: hooks_obj.on_unload(ctx) if hooks_obj and hooks_obj.on_unload else None,
    ),
  ]

  for hook_name, hook_fn in hook_order:
    # Check if hook is defined
    hook_callable = getattr(hooks_obj, hook_name, None) if hooks_obj else None
    if not hook_callable:
      _info(f"{hook_name}: not defined")
      continue

    try:
      result = hook_fn()
      if asyncio.iscoroutine(result):
        result = await result
      msg = f"{hook_name}: OK"
      if result is not None:
        msg += " (returned value)"
      _pass(msg)
      if verbose:
        logs = inspect.get_logs()
        if logs:
          _info(f"  logs: {logs[-1]}")
    except Exception as exc:
      _fail(f"{hook_name}: threw {exc}")
      if verbose:
        import traceback

        traceback.print_exc()

  print()

  # -------------------------------------------------------------------
  # 3. Test setup flow
  # -------------------------------------------------------------------
  if skill.has_setup and hooks_obj:
    has_start = hooks_obj.on_setup_start is not None
    has_submit = hooks_obj.on_setup_submit is not None
    has_cancel = hooks_obj.on_setup_cancel is not None

    if has_start or has_submit or has_cancel:
      print(bold("Setup Flow"))

      # 3a. on_setup_start
      step: SetupStep | None = None
      if has_start:
        try:
          step = await hooks_obj.on_setup_start(ctx)
          if isinstance(step, SetupStep) and step.fields:
            _pass(f'on_setup_start: returned step "{step.id}" with {len(step.fields)} field(s)')
          else:
            _fail("on_setup_start: must return SetupStep with at least one field")
            step = None
        except Exception as exc:
          _fail(f"on_setup_start: threw {exc}")
          if verbose:
            import traceback

            traceback.print_exc()
      else:
        _info("on_setup_start: not defined")

      # 3b. on_setup_submit with generated dummy values
      if has_submit and step:
        dummy_values: dict[str, Any] = {}
        for field in step.fields:
          if field.type == "text" or field.type == "password":
            dummy_values[field.name] = field.default if field.default is not None else "test-value"
          elif field.type == "number":
            dummy_values[field.name] = field.default if field.default is not None else 42
          elif field.type == "boolean":
            dummy_values[field.name] = field.default if field.default is not None else True
          elif field.type == "select":
            if field.options:
              dummy_values[field.name] = field.options[0].value
            else:
              dummy_values[field.name] = "option-1"
          elif field.type == "multiselect":
            if field.options:
              dummy_values[field.name] = [field.options[0].value]
            else:
              dummy_values[field.name] = []

        try:
          result = await hooks_obj.on_setup_submit(ctx, step.id, dummy_values)
          if isinstance(result, SetupResult) and result.status in (
            "next",
            "error",
            "complete",
          ):
            _pass(f'on_setup_submit: returned status="{result.status}"')
          else:
            _fail("on_setup_submit: must return SetupResult with valid status")
        except Exception as exc:
          _fail(f"on_setup_submit: threw {exc}")
          if verbose:
            import traceback

            traceback.print_exc()
      elif has_submit:
        _info("on_setup_submit: skipped (no step from on_setup_start)")
      else:
        _info("on_setup_submit: not defined")

      # 3c. on_setup_cancel
      if has_cancel:
        try:
          await hooks_obj.on_setup_cancel(ctx)
          _pass("on_setup_cancel: OK")
        except Exception as exc:
          _fail(f"on_setup_cancel: threw {exc}")
          if verbose:
            import traceback

            traceback.print_exc()
      else:
        _info("on_setup_cancel: not defined")

      print()

  # -------------------------------------------------------------------
  # 4. Test tools
  # -------------------------------------------------------------------
  if skill.tools:
    print(bold(f"Tools ({len(skill.tools)})"))

    for tool in skill.tools:
      defn = tool.definition
      if not defn.name:
        _fail("Tool missing name")
        continue
      if not defn.description:
        _warn(f'Tool "{defn.name}": missing description')
      params = defn.parameters
      if not params or params.get("type") != "object":
        _fail(f'Tool "{defn.name}": parameters must be {{"type": "object", ...}}')
        continue

      # Generate args from schema
      props = params.get("properties", {})
      generated_args = {k: generate_arg(v) for k, v in props.items()}

      try:
        result = await tool.execute(generated_args)
        if hasattr(result, "content") and isinstance(result.content, str):
          content_preview = result.content[:80]
          if len(result.content) > 80:
            content_preview += "..."
          _pass(f'{defn.name}: returned "{content_preview}"')
        else:
          _fail(f"{defn.name}: execute() must return ToolResult with content string")
      except Exception as exc:
        _fail(f"{defn.name}: threw {exc}")
        if verbose:
          import traceback

          traceback.print_exc()

    print()

  # -------------------------------------------------------------------
  # 5. Summary
  # -------------------------------------------------------------------
  if verbose:
    print(bold("Mock Context State"))
    _info(f"Logs: {len(inspect.get_logs())}")
    _info(f"Data files: {len(inspect.get_data())}")
    _info(f"Registered tools: {len(inspect.get_registered_tools())}")
    _info(f"Emitted events: {len(inspect.get_emitted_events())}")
    print()

  _print_summary()
  return 1 if fail_count > 0 else 0


def _print_summary() -> None:
  print(bold("Summary"))
  print(f"  {PASS} {pass_count} passed   {FAIL} {fail_count} failed   {WARN} {warn_count} warnings")
  print()


def main() -> None:
  args = sys.argv[1:]
  verbose = "--verbose" in args
  skill_dir = next((a for a in args if not a.startswith("--")), None)

  if not skill_dir:
    print("Usage: python -m dev.harness.runner <skill-dir> [--verbose]", file=sys.stderr)
    sys.exit(1)

  exit_code = asyncio.run(_run(skill_dir, verbose))
  sys.exit(exit_code)


if __name__ == "__main__":
  main()
