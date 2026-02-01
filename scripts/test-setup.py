#!/usr/bin/env python3
"""
Interactive setup flow tester.

Loads a skill, calls its setup hooks, and renders each step as a
terminal form. Collects user input and drives the flow to completion.

Usage:
    python scripts/test-setup.py <skill-dir>
    python scripts/test-setup.py skills/telegram

The script expects the skill directory to contain a skill.py (bundled
skills) or a setup.py module with on_setup_start / on_setup_submit /
on_setup_cancel functions.
"""

from __future__ import annotations

import asyncio
import getpass
import importlib.util
import sys
from pathlib import Path
from typing import Any

# Ensure repo root is importable
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dev.types.setup_types import SetupField, SetupResult, SetupStep

# ---------------------------------------------------------------------------
# Console helpers
# ---------------------------------------------------------------------------

BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RESET = "\033[0m"


def bold(s: str) -> str:
    return f"{BOLD}{s}{RESET}"


def dim(s: str) -> str:
    return f"{DIM}{s}{RESET}"


def green(s: str) -> str:
    return f"{GREEN}{s}{RESET}"


def red(s: str) -> str:
    return f"{RED}{s}{RESET}"


def yellow(s: str) -> str:
    return f"{YELLOW}{s}{RESET}"


def cyan(s: str) -> str:
    return f"{CYAN}{s}{RESET}"


# ---------------------------------------------------------------------------
# Mock context (minimal, for setup flow only)
# ---------------------------------------------------------------------------


class _SetupMockContext:
    """Lightweight mock context that supports write_data for config persistence."""

    def __init__(self, data_dir: str) -> None:
        self._data_dir = data_dir
        self._data: dict[str, str] = {}
        self._state: dict[str, Any] = {}

    @property
    def data_dir(self) -> str:
        return self._data_dir

    async def read_data(self, filename: str) -> str:
        return self._data.get(filename, "")

    async def write_data(self, filename: str, content: str) -> None:
        self._data[filename] = content
        # Also write to disk inside the skill's data/ directory
        data_path = Path(self._data_dir) / filename
        data_path.parent.mkdir(parents=True, exist_ok=True)
        data_path.write_text(content)
        print(dim(f"  [saved {data_path}]"))

    def log(self, message: str) -> None:
        print(dim(f"  [log] {message}"))

    def get_state(self) -> Any:
        return self._state

    def set_state(self, partial: dict[str, Any]) -> None:
        self._state.update(partial)

    def emit_event(self, event_name: str, data: Any) -> None:
        pass

    # Stubs so the context satisfies protocol checks
    class _NoOp:
        async def read(self, *a: Any, **kw: Any) -> Any:
            return None

        async def write(self, *a: Any, **kw: Any) -> None:
            pass

        async def search(self, *a: Any, **kw: Any) -> list:
            return []

        async def list(self, *a: Any, **kw: Any) -> list:
            return []

        async def delete(self, *a: Any, **kw: Any) -> None:
            pass

        async def get_by_tag(self, *a: Any, **kw: Any) -> list:
            return []

        async def get_by_id(self, *a: Any, **kw: Any) -> Any:
            return None

        def register(self, *a: Any, **kw: Any) -> None:
            pass

        def unregister(self, *a: Any, **kw: Any) -> None:
            pass

        @property
        def id(self) -> str:
            return "setup-test"

        def get(self, key: str) -> Any:
            return None

        def set(self, key: str, value: Any) -> None:
            pass

    memory = _NoOp()
    session = _NoOp()
    tools = _NoOp()
    entities = _NoOp()


# ---------------------------------------------------------------------------
# Skill loader
# ---------------------------------------------------------------------------


def load_setup_hooks(
    skill_dir: Path,
) -> tuple[Any, Any, Any]:
    """
    Load setup hooks from a skill directory.

    Tries in order:
      1. skill.py — look for hooks.on_setup_start etc.
      2. setup.py — look for on_setup_start, on_setup_submit, on_setup_cancel
    """
    # Try skill.py first
    skill_py = skill_dir / "skill.py"
    if skill_py.exists():
        spec = importlib.util.spec_from_file_location("_skill", skill_py)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            skill_obj = getattr(mod, "skill", None)
            if skill_obj:
                hooks = getattr(skill_obj, "hooks", None)
                if hooks:
                    start = getattr(hooks, "on_setup_start", None)
                    submit = getattr(hooks, "on_setup_submit", None)
                    cancel = getattr(hooks, "on_setup_cancel", None)
                    if start and submit:
                        return start, submit, cancel

    # Try setup.py
    setup_py = skill_dir / "setup.py"
    if setup_py.exists():
        spec = importlib.util.spec_from_file_location("_setup", setup_py)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            start = getattr(mod, "on_setup_start", None)
            submit = getattr(mod, "on_setup_submit", None)
            cancel = getattr(mod, "on_setup_cancel", None)
            if start and submit:
                return start, submit, cancel

    raise RuntimeError(
        f"No setup hooks found in {skill_dir}. "
        "Expected skill.py (with has_setup + hooks) or setup.py "
        "(with on_setup_start, on_setup_submit)."
    )


# ---------------------------------------------------------------------------
# Terminal form renderer
# ---------------------------------------------------------------------------


def render_step(step: SetupStep) -> None:
    """Print the step header and field descriptions."""
    print()
    print(f"  {bold(step.title)}")
    if step.description:
        print(f"  {dim(step.description)}")
    print()


def collect_field(field: SetupField) -> Any:
    """Collect a single field value from stdin."""
    label = f"  {field.label}"
    if field.description:
        label += f" {dim(f'({field.description})')}"
    if not field.required:
        label += f" {dim('[optional]')}"

    # Select / multiselect: show options
    if field.type in ("select", "multiselect") and field.options:
        print(label)
        for i, opt in enumerate(field.options, 1):
            print(f"    {cyan(str(i))}. {opt.label} {dim(f'({opt.value})')}")
        if field.type == "select":
            while True:
                raw = input(f"  Choice [1-{len(field.options)}]: ").strip()
                if raw.isdigit() and 1 <= int(raw) <= len(field.options):
                    return field.options[int(raw) - 1].value
                print(red(f"  Enter a number between 1 and {len(field.options)}"))
        else:
            # multiselect
            raw = input(f"  Choices (comma-separated) [1-{len(field.options)}]: ").strip()
            indices = [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]
            return [field.options[i - 1].value for i in indices if 1 <= i <= len(field.options)]

    # Boolean
    if field.type == "boolean":
        default_str = "Y/n" if field.default is True else "y/N"
        raw = input(f"{label} [{default_str}]: ").strip().lower()
        if not raw:
            return field.default if field.default is not None else False
        return raw in ("y", "yes", "true", "1")

    # Number
    if field.type == "number":
        placeholder = f" [{field.placeholder}]" if field.placeholder else ""
        while True:
            raw = input(f"{label}{placeholder}: ").strip()
            if not raw and not field.required:
                return field.default
            if not raw and field.required:
                print(red("  This field is required"))
                continue
            try:
                return float(raw) if "." in raw else int(raw)
            except ValueError:
                print(red("  Must be a number"))

    # Password
    if field.type == "password":
        while True:
            raw = getpass.getpass(f"{label}: ")
            if raw or not field.required:
                return raw
            print(red("  This field is required"))

    # Text (default)
    placeholder = f" [{field.placeholder}]" if field.placeholder else ""
    while True:
        raw = input(f"{label}{placeholder}: ").strip()
        if raw:
            return raw
        if not field.required:
            return field.default or ""
        print(red("  This field is required"))


def collect_values(step: SetupStep) -> dict[str, Any]:
    """Collect all field values for a step."""
    values: dict[str, Any] = {}
    for field in step.fields:
        values[field.name] = collect_field(field)
    return values


def show_errors(errors: list[Any]) -> None:
    """Display field-level validation errors."""
    print()
    for err in errors:
        field_label = f"[{err.field}] " if err.field else ""
        print(f"  {red('Error:')} {field_label}{err.message}")
    print()


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------


async def run_setup(skill_dir: str) -> int:
    abs_dir = Path(skill_dir).resolve()
    skill_name = abs_dir.name

    print()
    print(bold(f"Setup: {skill_name}"))
    print(dim(f"  Directory: {abs_dir}"))

    # Add skill parent to path so internal imports work
    if str(abs_dir.parent) not in sys.path:
        sys.path.insert(0, str(abs_dir.parent))

    on_start, on_submit, on_cancel = load_setup_hooks(abs_dir)

    data_dir = str(abs_dir / "data")
    ctx = _SetupMockContext(data_dir)

    # Get first step
    step: SetupStep = await on_start(ctx)

    while True:
        render_step(step)
        values = collect_values(step)

        result: SetupResult = await on_submit(ctx, step.id, values)

        if result.status == "complete":
            print()
            print(f"  {green('✓')} {bold('Setup complete!')}")
            if result.message:
                print(f"  {result.message}")
            print()
            return 0

        if result.status == "error":
            if result.errors:
                show_errors(result.errors)
            else:
                print(red("\n  Unknown error occurred.\n"))
            # Re-render the same step for retry
            print(dim("  Please try again."))
            continue

        if result.status == "next":
            if result.next_step:
                step = result.next_step
                continue
            else:
                print(red("\n  Server returned 'next' but no next step.\n"))
                return 1

        print(red(f"\n  Unknown status: {result.status}\n"))
        return 1


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(
            "Usage: python scripts/test-setup.py <skill-dir>\n"
            "       python scripts/test-setup.py skills/telegram",
            file=sys.stderr,
        )
        sys.exit(1)

    skill_dir = args[0]

    try:
        exit_code = asyncio.run(run_setup(skill_dir))
    except KeyboardInterrupt:
        print(f"\n\n  {yellow('Cancelled by user.')}\n")
        exit_code = 130
    except Exception as exc:
        print(f"\n  {red(f'Fatal error: {exc}')}\n")
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
