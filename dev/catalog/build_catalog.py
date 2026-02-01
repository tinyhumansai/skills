"""
Build a skills catalog JSON file.

Scans ../skills/ for production skills, extracts metadata from skill.py
exports and package.json, then writes skills-catalog.json to the
repository root.

Usage:
    python -m dev.catalog.build_catalog
"""

from __future__ import annotations

import ast
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add repo root to sys.path if running as script (not as module)
if __name__ == "__main__" and __file__:
  script_path = Path(__file__).resolve()
  repo_root = script_path.parent.parent.parent
  if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from dev.types.skill_types import SkillDefinition

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


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


def detect_execution_style(dir_path: Path) -> str:
  """Detect skill execution style from directory contents."""
  has_skill_py = (dir_path / "skill.py").exists()
  has_pkg_json = (dir_path / "package.json").exists()
  has_src_dir = (dir_path / "src").is_dir()
  has_ts_files = any(dir_path.rglob("*.ts"))

  if has_skill_py:
    return "python"
  if has_pkg_json and has_src_dir:
    return "integration"
  if has_ts_files:
    return "integration"
  return "prompt-only"


# ---------------------------------------------------------------------------
# Metadata extraction
# ---------------------------------------------------------------------------


def extract_skill_py_fallback(skill_py_path: Path) -> dict[str, Any] | None:
  """Fallback: Extract metadata from skill.py using AST/regex when imports fail."""
  try:
    content = skill_py_path.read_text(encoding="utf-8")
  except Exception:
    return None

  result: dict[str, Any] = {}

  # Extract name, description, version using regex (simple and reliable)
  name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
  if name_match:
    result["name"] = name_match.group(1)

  desc_match = re.search(r'description\s*=\s*["\']([^"\']+)["\']', content)
  if desc_match:
    result["description"] = desc_match.group(1)

  version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
  if version_match:
    result["version"] = version_match.group(1)

  # Extract tick_interval and convert to minutes
  tick_match = re.search(r"tick_interval\s*=\s*(\d+)", content)
  if tick_match:
    tick_ms = int(tick_match.group(1))
    # Convert milliseconds to minutes (round to 1 decimal place)
    result["tick_interval_minutes"] = round(tick_ms / 60_000, 1)

  # Try to extract tools using AST (more reliable than regex)
  try:
    tree = ast.parse(content, filename=str(skill_py_path))

    # Find the skill = SkillDefinition(...) assignment
    for node in ast.walk(tree):
      if isinstance(node, ast.Assign):
        for target in node.targets:
          if isinstance(target, ast.Name) and target.id == "skill":
            if isinstance(node.value, ast.Call):
              # Extract tools from SkillDefinition call
              tools: list[str] = []
              hooks: list[str] = []

              # Look for tools= argument
              for keyword in node.value.keywords:
                if keyword.arg == "tools":
                  # Try to extract tool names
                  if isinstance(keyword.value, (ast.List, ast.Tuple)):
                    for elt in keyword.value.elts:
                      # Look for SkillTool(...) calls
                      if isinstance(elt, ast.Call):
                        # Find name= in ToolDefinition
                        for kw in elt.keywords:
                          if kw.arg == "definition":
                            # This is a ToolDefinition call
                            if isinstance(kw.value, ast.Call):
                              for def_kw in kw.value.keywords:
                                if def_kw.arg == "name":
                                  if isinstance(def_kw.value, ast.Constant):
                                    tools.append(def_kw.value.value)

                  # Also check for variable reference (e.g., tools=_TOOLS)
                  elif isinstance(keyword.value, ast.Name):
                    # Find the variable definition
                    var_name = keyword.value.id
                    for stmt in ast.walk(tree):
                      if isinstance(stmt, ast.Assign):
                        for tgt in stmt.targets:
                          if isinstance(tgt, ast.Name) and tgt.id == var_name:
                            if isinstance(stmt.value, (ast.List, ast.Tuple)):
                              for elt in stmt.value.elts:
                                if isinstance(elt, ast.Call):
                                  for kw in elt.keywords:
                                    if kw.arg == "definition" and isinstance(kw.value, ast.Call):
                                      for def_kw in kw.value.keywords:
                                        if def_kw.arg == "name" and isinstance(
                                          def_kw.value,
                                          ast.Constant,
                                        ):
                                          tools.append(def_kw.value.value)

              # Look for hooks= argument
              for keyword in node.value.keywords:
                if keyword.arg == "hooks":
                  if isinstance(keyword.value, ast.Call):
                    # SkillHooks(...)
                    for kw in keyword.value.keywords:
                      hook_name = kw.arg
                      if hook_name and kw.value is not None:
                        # Check if it's not None
                        if not (isinstance(kw.value, ast.Constant) and kw.value.value is None):
                          hooks.append(hook_name)

              # Look for tick_interval= argument
              for keyword in node.value.keywords:
                if keyword.arg == "tick_interval":
                  if isinstance(keyword.value, ast.Constant):
                    tick_ms = keyword.value.value
                    if isinstance(tick_ms, int):
                      result["tick_interval_minutes"] = round(tick_ms / 60_000, 1)

              if tools:
                result["tools"] = tools
              if hooks:
                result["hooks"] = hooks

              break
  except Exception:
    # AST parsing failed, fall back to regex for tools
    # Count SkillTool occurrences as a rough estimate
    tool_count = len(re.findall(r"SkillTool\s*\(", content))
    if tool_count > 0:
      # Try to extract tool names from name= patterns
      tool_names = re.findall(r'name\s*=\s*["\']([a-z_][a-z0-9_]*)["\']', content)
      # Filter out common non-tool names
      filtered_tools = [
        n
        for n in tool_names
        if n
        not in (
          "on_load",
          "on_unload",
          "on_tick",
          "on_session_start",
          "on_session_end",
          "on_before_message",
          "on_after_response",
        )
      ]
      if filtered_tools:
        result["tools"] = filtered_tools

    # Extract hooks using regex
    hooks_found = []
    for hook in (
      "on_load",
      "on_unload",
      "on_session_start",
      "on_session_end",
      "on_before_message",
      "on_after_response",
      "on_memory_flush",
      "on_tick",
    ):
      if re.search(rf"{hook}\s*=\s*\w", content):
        hooks_found.append(hook)
    if hooks_found:
      result["hooks"] = hooks_found

  return result if result else None


def extract_skill_py(skill_py_path: Path) -> dict[str, Any] | None:
  """Extract metadata from skill.py via dynamic import."""
  if not skill_py_path.exists():
    return None

  try:
    # Determine the package structure
    # skill_py_path is like: /path/to/skills/telegram/skill.py
    # We need: skills.telegram as the package name
    repo_root = skill_py_path.parent.parent.parent
    skill_dir = skill_py_path.parent
    skill_dir_name = skill_dir.name

    # Ensure repo root is in sys.path for absolute imports (dev.types, etc.)
    if str(repo_root) not in sys.path:
      sys.path.insert(0, str(repo_root))

    # Set up module name and package for relative imports
    # Module name should be skills.<skill_name>.skill
    module_name = f"skills.{skill_dir_name}.skill"

    spec = importlib.util.spec_from_file_location(module_name, skill_py_path)
    if spec is None or spec.loader is None:
      return None

    module = importlib.util.module_from_spec(spec)
    # Set __package__ so relative imports work (e.g., "from .setup import ...")
    module.__package__ = f"skills.{skill_dir_name}"
    module.__name__ = module_name

    spec.loader.exec_module(module)
  except Exception as exc:
    # Import failed (likely missing dependencies), try fallback extraction
    print(f"  {WARN} Failed to import {skill_py_path}: {exc}", file=sys.stderr)
    fallback_data = extract_skill_py_fallback(skill_py_path)
    if fallback_data:
      return fallback_data
    return None

  skill_obj = getattr(module, "skill", None)
  if skill_obj is None:
    return None

  # Coerce to SkillDefinition if needed
  skill: SkillDefinition
  if isinstance(skill_obj, SkillDefinition):
    skill = skill_obj
  else:
    try:
      skill = SkillDefinition.model_validate(skill_obj)
    except Exception:
      return None

  tools: list[str] = []
  for tool in skill.tools:
    if tool.definition and tool.definition.name:
      tools.append(tool.definition.name)

  hooks: list[str] = []
  if skill.hooks:
    for field_name in [
      "on_load",
      "on_unload",
      "on_session_start",
      "on_session_end",
      "on_before_message",
      "on_after_response",
      "on_memory_flush",
      "on_tick",
    ]:
      if getattr(skill.hooks, field_name, None) is not None:
        hooks.append(field_name)

  # Convert tick_interval from milliseconds to minutes
  tick_interval_minutes = None
  if skill.tick_interval is not None:
    tick_interval_minutes = round(skill.tick_interval / 60_000, 1)

  return {
    "name": skill.name,
    "description": skill.description,
    "version": skill.version,
    "tools": tools,
    "hooks": hooks,
    "tick_interval_minutes": tick_interval_minutes,
  }


def read_pkg_json(pkg_json_path: Path) -> dict[str, str] | None:
  """Read metadata from package.json."""
  try:
    data = json.loads(pkg_json_path.read_text(encoding="utf-8"))
    return {
      "name": data.get("name", ""),
      "description": data.get("description", ""),
      "version": data.get("version", ""),
    }
  except Exception:
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
  dev_dir = Path(__file__).resolve().parent.parent
  root_dir = dev_dir.parent
  skills_dir = root_dir / "skills"
  output_path = root_dir / "skills-catalog.json"

  print(file=sys.stderr)
  print(bold("AlphaHuman Skills Catalog Builder"), file=sys.stderr)
  print(file=sys.stderr)

  # 1. Read all subdirectories of skills/
  if not skills_dir.is_dir():
    print(f"  {FAIL} Cannot read skills directory: {skills_dir}", file=sys.stderr)
    sys.exit(1)

  entries = sorted(
    e.name
    for e in skills_dir.iterdir()
    if e.is_dir() and not e.name.startswith(".") and e.name != "__pycache__"
  )

  if not entries:
    print(f"  {WARN} No skill directories found in {skills_dir}", file=sys.stderr)
    sys.exit(0)

  print(
    f"  Found {len(entries)} skill director{'y' if len(entries) == 1 else 'ies'}.",
    file=sys.stderr,
  )
  print(file=sys.stderr)

  catalog_entries: list[dict[str, Any]] = []
  seen_names: set[str] = set()
  warnings = 0

  for dir_name in entries:
    dir_path = skills_dir / dir_name
    rel_path = f"skills/{dir_name}"

    # 2. Parse metadata
    skill_data = extract_skill_py(dir_path / "skill.py")
    pkg_data = read_pkg_json(dir_path / "package.json")

    # 3. Determine name (priority: skill.py > package.json > dirName)
    name = (skill_data or {}).get("name") or (pkg_data or {}).get("name") or dir_name

    # 4. Check for duplicates
    if name in seen_names:
      print(f'  {WARN} Duplicate skill name: "{name}" (in {rel_path})', file=sys.stderr)
      warnings += 1
    seen_names.add(name)

    # 5. Determine description
    description = (skill_data or {}).get("description") or (pkg_data or {}).get("description") or ""
    if not description:
      print(f"  {WARN} No description found for {rel_path}", file=sys.stderr)
      warnings += 1

    # 6. Build entry
    entry: dict[str, Any] = {
      "name": name,
      "description": description,
      "icon": None,
      "version": ((skill_data or {}).get("version") or (pkg_data or {}).get("version") or None),
      "tools": (skill_data or {}).get("tools", []),
      "hooks": (skill_data or {}).get("hooks", []),
      "tickIntervalMinutes": (skill_data or {}).get("tick_interval_minutes"),
      "path": rel_path,
    }

    catalog_entries.append(entry)
    print(f"  {PASS} {name}", file=sys.stderr)

  # 8. Sort alphabetically
  catalog_entries.sort(key=lambda e: e["name"])

  # 9. Write catalog
  catalog = {
    "generatedAt": datetime.now(timezone.utc).isoformat(),
    "version": "1.0.0",
    "skills": catalog_entries,
  }

  output_path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")

  # 10. Summary
  print(file=sys.stderr)
  print(bold("Summary"), file=sys.stderr)
  print(file=sys.stderr)
  print(f"  Skills:   {len(catalog_entries)}", file=sys.stderr)
  print(f"  {WARN} Warnings: {warnings}", file=sys.stderr)

  try:
    rel_output = output_path.relative_to(Path.cwd())
  except ValueError:
    rel_output = output_path
  print(f"  Output:   {rel_output}", file=sys.stderr)
  print(file=sys.stderr)


if __name__ == "__main__":
  main()
