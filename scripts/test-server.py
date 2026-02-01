#!/usr/bin/env python3
"""
Interactive Telegram skill server tester.

Connects to Telegram using credentials from setup (or env vars),
loads the skill, and provides an interactive REPL to browse and
call any of the 75+ tools.

Usage:
    python scripts/test-server.py [skills/telegram]

    # With env vars (skips credential prompts):
    TELEGRAM_API_ID=12345 TELEGRAM_API_HASH=abc... python scripts/test-server.py

The script looks for a saved session in skills/telegram/data/config.json
(written by test-setup.py). If none exists, it runs the setup flow first.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import readline  # enables arrow-key history in input()
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SKILL_DIR = ROOT / "skills" / "telegram"
DATA_DIR = SKILL_DIR / "data"
CONFIG_PATH = DATA_DIR / "config.json"

# Add skills/ to path so `from telegram.xxx` imports work
if str(SKILL_DIR.parent) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR.parent))

# ---------------------------------------------------------------------------
# Logging — show skill logs in real-time
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="\033[2m[%(name)s] %(message)s\033[0m",
    stream=sys.stderr,
)
log = logging.getLogger("test-server")

# ---------------------------------------------------------------------------
# Console helpers
# ---------------------------------------------------------------------------

BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
RESET = "\033[0m"


def bold(s: str) -> str:
    return f"{BOLD}{s}{RESET}"


def dim(s: str) -> str:
    return f"{DIM}{s}{RESET}"


def green(s: str) -> str:
    return f"{GREEN}{s}{RESET}"


def red(s: str) -> str:
    return f"{RED}{s}{RESET}"


def cyan(s: str) -> str:
    return f"{CYAN}{s}{RESET}"


def magenta(s: str) -> str:
    return f"{MAGENTA}{s}{RESET}"


def yellow(s: str) -> str:
    return f"{YELLOW}{s}{RESET}"


# ---------------------------------------------------------------------------
# Config / session management
# ---------------------------------------------------------------------------


def load_config() -> dict[str, Any] | None:
    """Load saved config from data/config.json."""
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text())
        except Exception:
            return None
    return None


def get_credentials() -> tuple[int, str, str]:
    """Get API credentials and session string from config or env vars.

    Returns (api_id, api_hash, session_string).
    """
    config = load_config()

    api_id = int(os.environ.get("TELEGRAM_API_ID", "0"))
    api_hash = os.environ.get("TELEGRAM_API_HASH", "")
    session_string = ""

    if config:
        if not api_id:
            api_id = config.get("api_id", 0)
        if not api_hash:
            api_hash = config.get("api_hash", "")
        session_string = config.get("session_string", "")

    return api_id, api_hash, session_string


# ---------------------------------------------------------------------------
# Setup flow (inline, reuses test-setup.py logic)
# ---------------------------------------------------------------------------


async def run_setup_if_needed() -> tuple[int, str, str]:
    """Check if we have valid credentials. If not, run the setup flow.

    Returns (api_id, api_hash, session_string).
    """
    api_id, api_hash, session_string = get_credentials()

    if api_id and api_hash and session_string:
        return api_id, api_hash, session_string

    if not api_id or not api_hash:
        print(yellow("\n  No credentials found. Running setup flow...\n"))
    elif not session_string:
        print(yellow("\n  No session found. Running setup flow...\n"))

    # Import and run test-setup inline
    import subprocess

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "test-setup.py"), str(SKILL_DIR)],
        cwd=str(ROOT),
    )
    if result.returncode != 0:
        print(red("  Setup failed."))
        sys.exit(1)

    # Reload config after setup
    api_id, api_hash, session_string = get_credentials()
    if not api_id or not api_hash or not session_string:
        print(red("  Setup completed but credentials not saved."))
        sys.exit(1)

    return api_id, api_hash, session_string


# ---------------------------------------------------------------------------
# Tool categories
# ---------------------------------------------------------------------------

CATEGORIES = [
    ("Chat", "chat_tools"),
    ("Message", "message_tools"),
    ("Contact", "contact_tools"),
    ("Admin", "admin_tools"),
    ("Media & Profile", "profile_media_tools"),
    ("Settings", "settings_tools"),
    ("Search", "search_tools"),
]


def build_tool_index(
    all_tools: list[Any],
) -> tuple[
    dict[str, list[Any]],  # category -> tools
    dict[str, Any],  # name -> tool
]:
    """Group tools by category and build lookup index."""
    from telegram.tools import (
        chat_tools,
        message_tools,
        contact_tools,
        admin_tools,
        profile_media_tools,
        settings_tools,
        search_tools,
    )

    groups = {
        "Chat": chat_tools,
        "Message": message_tools,
        "Contact": contact_tools,
        "Admin": admin_tools,
        "Media & Profile": profile_media_tools,
        "Settings": settings_tools,
        "Search": search_tools,
    }

    by_name: dict[str, Any] = {}
    for tool in all_tools:
        by_name[tool.name] = tool

    return groups, by_name


# ---------------------------------------------------------------------------
# Interactive REPL
# ---------------------------------------------------------------------------


def show_categories(groups: dict[str, list[Any]]) -> None:
    """Show tool categories with counts."""
    print()
    print(bold("  Tool Categories"))
    print()
    for i, (cat, tools) in enumerate(groups.items(), 1):
        print(f"    {cyan(str(i))}. {cat} ({len(tools)} tools)")
    print()
    print(f"    {cyan('s')}. Search tools by name")
    print(f"    {cyan('a')}. List all tools")
    print(f"    {cyan('q')}. Quit")
    print()


def show_tools_in_category(category: str, tools: list[Any]) -> None:
    """Show tools within a category."""
    print()
    print(bold(f"  {category}"))
    print()
    for i, tool in enumerate(tools, 1):
        print(f"    {cyan(str(i))}. {bold(tool.name)}")
        desc = tool.description or ""
        if desc:
            print(f"       {dim(desc)}")
    print()
    print(f"    {cyan('b')}. Back to categories")
    print()


def show_tool_detail(tool: Any) -> None:
    """Show full tool details with its input schema."""
    print()
    print(f"  {bold(tool.name)}")
    if tool.description:
        print(f"  {dim(tool.description)}")
    print()

    schema = tool.inputSchema or {}
    props = schema.get("properties", {})
    required = set(schema.get("required", []))

    if props:
        print(f"  {bold('Parameters:')}")
        for name, prop in props.items():
            req_tag = f" {red('*')}" if name in required else ""
            ptype = prop.get("type", "any")
            desc = prop.get("description", "")
            default = prop.get("default")
            enum = prop.get("enum")

            line = f"    {cyan(name)}{req_tag} ({dim(ptype)})"
            if desc:
                line += f" — {desc}"
            if default is not None:
                line += f" [default: {default}]"
            if enum:
                line += f" [{', '.join(str(e) for e in enum)}]"
            print(line)
        print()
    else:
        print(f"  {dim('No parameters')}")
        print()


def collect_tool_args(tool: Any) -> dict[str, Any] | None:
    """Interactively collect arguments for a tool call.

    Returns None if user wants to cancel.
    """
    schema = tool.inputSchema or {}
    props = schema.get("properties", {})
    required = set(schema.get("required", []))

    if not props:
        return {}

    args: dict[str, Any] = {}
    for name, prop in props.items():
        is_required = name in required
        ptype = prop.get("type", "string")
        default = prop.get("default")
        enum = prop.get("enum")
        desc = prop.get("description", "")

        label = f"    {name}"
        if desc:
            label += f" {dim(f'({desc})')}"
        if not is_required:
            label += f" {dim('[optional]')}"

        # Enum selection
        if enum:
            print(label)
            for i, val in enumerate(enum, 1):
                print(f"      {cyan(str(i))}. {val}")
            raw = input(f"    Choice [1-{len(enum)}]: ").strip()
            if raw == "":
                if not is_required:
                    if default is not None:
                        args[name] = default
                    continue
                print(red("    Required field"))
                return collect_tool_args(tool)
            if raw.isdigit() and 1 <= int(raw) <= len(enum):
                args[name] = enum[int(raw) - 1]
            else:
                args[name] = raw
            continue

        # Default display
        default_hint = ""
        if default is not None:
            default_hint = f" [{default}]"

        raw = input(f"{label}{default_hint}: ").strip()

        if raw == "" and not is_required:
            if default is not None:
                args[name] = default
            continue
        if raw == "" and is_required:
            print(red("    Required field"))
            return collect_tool_args(tool)
        if raw.lower() == "!cancel":
            return None

        # Type coercion
        if ptype == "number":
            try:
                args[name] = float(raw) if "." in raw else int(raw)
            except ValueError:
                args[name] = raw
        elif ptype == "boolean":
            args[name] = raw.lower() in ("true", "yes", "1", "y")
        elif ptype == "array":
            # Comma-separated values
            args[name] = [v.strip() for v in raw.split(",") if v.strip()]
        else:
            args[name] = raw

    return args


async def tool_repl(
    groups: dict[str, list[Any]],
    by_name: dict[str, Any],
    dispatch_fn: Any,
) -> None:
    """Main interactive REPL loop."""
    cat_list = list(groups.items())

    while True:
        show_categories(groups)
        choice = input("  > ").strip().lower()

        if choice in ("q", "quit", "exit"):
            break

        # Search
        if choice == "s":
            query = input("  Search: ").strip().lower()
            if not query:
                continue
            matches = [
                t
                for name, t in by_name.items()
                if query in name.lower() or query in (t.description or "").lower()
            ]
            if not matches:
                print(yellow("  No tools found."))
                continue
            print()
            print(bold(f"  Search results ({len(matches)})"))
            print()
            for i, t in enumerate(matches, 1):
                print(f"    {cyan(str(i))}. {bold(t.name)} — {dim(t.description or '')}")
            print()
            pick = input("  Tool # (or Enter to go back): ").strip()
            if pick.isdigit() and 1 <= int(pick) <= len(matches):
                await call_tool_interactive(matches[int(pick) - 1], dispatch_fn)
            continue

        # All tools
        if choice == "a":
            all_list = list(by_name.values())
            print()
            print(bold(f"  All Tools ({len(all_list)})"))
            print()
            for i, t in enumerate(all_list, 1):
                print(f"    {cyan(f'{i:>3}')}. {bold(t.name)} — {dim(t.description or '')}")
            print()
            pick = input("  Tool # (or Enter to go back): ").strip()
            if pick.isdigit() and 1 <= int(pick) <= len(all_list):
                await call_tool_interactive(all_list[int(pick) - 1], dispatch_fn)
            continue

        # Direct tool name
        if choice in by_name:
            await call_tool_interactive(by_name[choice], dispatch_fn)
            continue

        # Category selection
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(cat_list):
                cat_name, cat_tools = cat_list[idx]
                await category_repl(cat_name, cat_tools, dispatch_fn)
            continue

        print(dim("  Enter a number, tool name, 's' to search, 'a' for all, or 'q' to quit."))


async def category_repl(
    category: str,
    tools: list[Any],
    dispatch_fn: Any,
) -> None:
    """REPL within a tool category."""
    while True:
        show_tools_in_category(category, tools)
        choice = input("  > ").strip().lower()

        if choice in ("b", "back", ""):
            return
        if choice in ("q", "quit", "exit"):
            sys.exit(0)

        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(tools):
                await call_tool_interactive(tools[idx], dispatch_fn)
            continue

        # Try matching by name
        for tool in tools:
            if tool.name == choice:
                await call_tool_interactive(tool, dispatch_fn)
                break


async def call_tool_interactive(tool: Any, dispatch_fn: Any) -> None:
    """Show tool details, collect args, call it, display result."""
    show_tool_detail(tool)

    confirm = input(f"  Call {bold(tool.name)}? [Y/n]: ").strip().lower()
    if confirm in ("n", "no"):
        return

    args = collect_tool_args(tool)
    if args is None:
        print(dim("  Cancelled."))
        return

    print()
    print(f"  {dim('Calling')} {bold(tool.name)}{dim('...')}")
    print()

    try:
        result = await dispatch_fn(tool.name, args)
        if result.is_error:
            print(f"  {red('Error:')}")
        else:
            print(f"  {green('Result:')}")
        print()
        # Pretty-print JSON if possible
        try:
            parsed = json.loads(result.content)
            formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
            for line in formatted.split("\n"):
                print(f"    {line}")
        except (json.JSONDecodeError, TypeError):
            for line in result.content.split("\n"):
                print(f"    {line}")
        print()
    except Exception as exc:
        print(f"  {red(f'Exception: {exc}')}")
        print()

    input(dim("  Press Enter to continue..."))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main_async() -> int:
    print()
    print(bold("  Telegram Skill Server Tester"))
    print()

    # 1. Get credentials (run setup if needed)
    api_id, api_hash, session_string = await run_setup_if_needed()

    print(dim(f"  API ID: {api_id}"))
    print(dim(f"  Session: {'found' if session_string else 'none'}"))
    print()

    # 2. Import and initialize the skill
    print(dim("  Loading skill..."))

    from telegram.server import on_skill_load, on_skill_unload
    from telegram.tools import ALL_TOOLS
    from telegram.handlers import dispatch_tool

    data_dir = str(DATA_DIR)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    await on_skill_load(
        {
            "apiId": str(api_id),
            "apiHash": api_hash,
            "sessionString": session_string,
            "dataDir": data_dir,
        }
    )

    from telegram.state import store

    state = store.get_state()

    if state.auth_status != "authenticated":
        print(red(f"  Authentication failed (status: {state.auth_status})"))
        print(yellow("  Try running: python scripts/test-setup.py skills/telegram"))
        await on_skill_unload()
        return 1

    user = state.current_user
    if user:
        name = user.first_name or user.username or str(user.id)
        print(green(f"  Connected as {name}"))
    else:
        print(green("  Connected"))

    print(dim(f"  {len(ALL_TOOLS)} tools available"))
    print()

    # 3. Build tool index
    groups, by_name = build_tool_index(ALL_TOOLS)

    # 4. Start REPL
    try:
        await tool_repl(groups, by_name, dispatch_tool)
    finally:
        print(dim("\n  Disconnecting..."))
        await on_skill_unload()
        print(dim("  Done.\n"))

    return 0


def main() -> None:
    try:
        code = asyncio.run(main_async())
    except KeyboardInterrupt:
        print(f"\n\n  {yellow('Interrupted.')}\n")
        code = 130
    sys.exit(code)


if __name__ == "__main__":
    main()
