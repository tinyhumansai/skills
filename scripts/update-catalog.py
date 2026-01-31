#!/usr/bin/env python3
"""
Update the skills catalog.

Scans skills/ for production skills, extracts metadata from skill.py
and manifest.json, and writes skills-catalog.json to the repo root.

Wraps dev.catalog.build_catalog with a friendlier CLI.

Usage:
    python scripts/update-catalog.py              # Build catalog
    python scripts/update-catalog.py --check      # Validate only (exit 1 if stale)
    python scripts/update-catalog.py --verbose     # Show per-skill details
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dev.catalog.build_catalog import main as build_catalog_main

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
# Check mode — compare existing catalog with fresh build
# ---------------------------------------------------------------------------


def check_catalog() -> int:
    """Compare existing catalog with a fresh build. Exit 1 if stale."""
    catalog_path = ROOT / "skills-catalog.json"

    if not catalog_path.exists():
        print(f"  {red('FAIL')} No skills-catalog.json found")
        print(f"  {dim('Run: python scripts/update-catalog.py')}")
        return 1

    try:
        existing = json.loads(catalog_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  {red('FAIL')} Cannot read catalog: {e}")
        return 1

    # Build a fresh catalog in memory by importing the builder internals
    from dev.catalog.build_catalog import (
        detect_execution_style,
        extract_skill_py,
        read_pkg_json,
    )

    skills_dir = ROOT / "skills"
    if not skills_dir.is_dir():
        print(f"  {red('FAIL')} No skills/ directory")
        return 1

    entries = sorted(
        e.name
        for e in skills_dir.iterdir()
        if e.is_dir() and not e.name.startswith(".")
    )

    fresh_skills: list[dict] = []
    for dir_name in entries:
        dir_path = skills_dir / dir_name
        style = detect_execution_style(dir_path)
        skill_data = extract_skill_py(dir_path / "skill.py")
        pkg_data = read_pkg_json(dir_path / "package.json")

        name = (
            (skill_data or {}).get("name")
            or (pkg_data or {}).get("name")
            or dir_name
        )
        description = (
            (skill_data or {}).get("description")
            or (pkg_data or {}).get("description")
            or ""
        )

        fresh_skills.append({
            "name": name,
            "description": description,
            "icon": None,
            "executionStyle": style,
            "version": (
                (skill_data or {}).get("version")
                or (pkg_data or {}).get("version")
                or None
            ),
            "tools": (skill_data or {}).get("tools", []),
            "hooks": (skill_data or {}).get("hooks", []),
            "tickInterval": (skill_data or {}).get("tick_interval"),
            "path": f"skills/{dir_name}",
        })

    fresh_skills.sort(key=lambda e: e["name"])

    # Compare skill entries (ignore generatedAt timestamp)
    existing_skills = existing.get("skills", [])

    if existing_skills == fresh_skills:
        print(f"  {green('OK')} Catalog is up to date ({len(fresh_skills)} skills)")
        return 0

    # Find differences
    existing_names = {s["name"] for s in existing_skills}
    fresh_names = {s["name"] for s in fresh_skills}

    added = fresh_names - existing_names
    removed = existing_names - fresh_names
    common = existing_names & fresh_names

    changed = 0
    for name in common:
        old = next(s for s in existing_skills if s["name"] == name)
        new = next(s for s in fresh_skills if s["name"] == name)
        if old != new:
            changed += 1

    print(f"  {yellow('STALE')} Catalog is out of date")
    if added:
        print(f"    Added:   {', '.join(sorted(added))}")
    if removed:
        print(f"    Removed: {', '.join(sorted(removed))}")
    if changed:
        print(f"    Changed: {changed} skill(s)")
    print(f"  {dim('Run: python scripts/update-catalog.py')}")
    return 1


# ---------------------------------------------------------------------------
# Verbose mode — show detailed per-skill info after building
# ---------------------------------------------------------------------------


def show_verbose(catalog_path: Path) -> None:
    """Print detailed catalog contents."""
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    except Exception:
        return

    skills = catalog.get("skills", [])
    print()
    print(bold("  Catalog Details"))
    print(f"  {'─' * 50}")
    print(f"  Generated: {dim(catalog.get('generatedAt', '?'))}")
    print(f"  Skills:    {green(str(len(skills)))}")
    print()

    for s in skills:
        name = s.get("name", "?")
        style = s.get("executionStyle", "?")
        version = s.get("version") or "?"
        tools = s.get("tools", [])
        hooks = s.get("hooks", [])
        tick = s.get("tickInterval")
        desc = s.get("description", "")

        print(f"  {bold(name)} {dim(f'v{version}')} {cyan(f'[{style}]')}")
        if desc:
            print(f"    {dim(desc[:80])}")
        if tools:
            print(f"    Tools: {len(tools)} — {dim(', '.join(tools[:5]))}")
            if len(tools) > 5:
                print(f"           {dim(f'... and {len(tools) - 5} more')}")
        if hooks:
            print(f"    Hooks: {dim(', '.join(hooks))}")
        if tick:
            print(f"    Tick:  {dim(f'{tick}ms')}")
        print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    args = sys.argv[1:]

    print()
    print(bold("  Skills Catalog Updater"))
    print()

    if "--check" in args:
        code = check_catalog()
        print()
        sys.exit(code)

    # Build the catalog using the existing builder
    build_catalog_main()

    catalog_path = ROOT / "skills-catalog.json"

    if "--verbose" in args or "-v" in args:
        show_verbose(catalog_path)

    if catalog_path.exists():
        print(f"  {green('Done.')} Catalog written to {dim(str(catalog_path.relative_to(ROOT)))}")
    print()


if __name__ == "__main__":
    main()
