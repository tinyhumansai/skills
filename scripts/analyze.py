#!/usr/bin/env python3
"""
Analyze Python files by line count.

Finds files exceeding a threshold and provides suggestions for splitting them.
"""

from __future__ import annotations

import ast
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# Path setup
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))


class FileAnalyzer:
  """Analyze a Python file's structure."""

  def __init__(self, file_path: Path):
    self.file_path = file_path
    self.content = file_path.read_text(encoding="utf-8")
    self.lines = self.content.splitlines()
    self.total_lines = len(self.lines)
    self.code_lines = self._count_code_lines()
    self.tree: ast.Module | None = None
    self._parse()

  def _count_code_lines(self) -> int:
    """Count non-empty, non-comment lines."""
    count = 0
    for line in self.lines:
      stripped = line.strip()
      if stripped and not stripped.startswith("#"):
        count += 1
    return count

  def _parse(self) -> None:
    """Parse the file as AST."""
    try:
      self.tree = ast.parse(self.content, filename=str(self.file_path))
    except SyntaxError:
      self.tree = None

  def get_imports(self) -> list[str]:
    """Extract import statements."""
    if not self.tree:
      return []
    imports = []
    for node in ast.walk(self.tree):
      if isinstance(node, ast.Import):
        for alias in node.names:
          imports.append(alias.name)
      elif isinstance(node, ast.ImportFrom):
        module = node.module or ""
        for alias in node.names:
          imports.append(f"{module}.{alias.name}")
    return imports

  def get_classes(self) -> list[dict[str, Any]]:
    """Extract class definitions with their line numbers."""
    if not self.tree:
      return []
    classes = []
    for node in ast.walk(self.tree):
      if isinstance(node, ast.ClassDef):
        classes.append(
          {
            "name": node.name,
            "line": node.lineno,
            "end_line": node.end_lineno or node.lineno,
            "methods": len([n for n in node.body if isinstance(n, ast.FunctionDef)]),
          }
        )
    return classes

  def get_functions(self) -> list[dict[str, Any]]:
    """Extract function definitions with their line numbers."""
    if not self.tree:
      return []
    functions = []

    # Build parent map
    parent_map = {}
    for node in ast.walk(self.tree):
      for child in ast.iter_child_nodes(node):
        parent_map[child] = node

    for node in ast.walk(self.tree):
      # Check for both FunctionDef and AsyncFunctionDef
      if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        # Only top-level functions (not methods)
        parent = parent_map.get(node)
        if not isinstance(parent, ast.ClassDef):
          functions.append(
            {
              "name": node.name,
              "line": node.lineno,
              "end_line": node.end_lineno or node.lineno,
            }
          )
    return functions

  def get_sections(self) -> list[dict[str, Any]]:
    """Identify logical sections in the file."""
    functions = self.get_functions()
    classes = self.get_classes()

    # First, check for explicit section markers (comment headers)
    sections = []
    current_section = None
    section_start = 1

    for i, line in enumerate(self.lines, 1):
      stripped = line.strip()

      # Section header comments (with separators or long descriptive comments)
      if stripped.startswith("#") and ("---" in stripped or "==" in stripped or len(stripped) > 50):
        if current_section:
          sections.append(
            {
              "name": current_section,
              "start": section_start,
              "end": i - 1,
            }  # type: ignore[dict-item]
          )
        current_section = stripped.strip("#").strip()
        section_start = i

    # If we found explicit sections, use them
    if sections or current_section:
      if current_section:
        sections.append(
          {
            "name": current_section,
            "start": section_start,
            "end": len(self.lines),
          }  # type: ignore[dict-item]
        )
      return sections

    # Otherwise, group by classes or function prefixes
    if len(classes) > 1:
      # Split by classes
      sections = []
      for cls in classes:
        cls_section: dict[str, Any] = {
          "name": f"Class: {cls['name']}",
          "start": cls["line"],
          "end": cls["end_line"],
        }
        sections.append(cls_section)
      return sections

    # Group functions by prefix if we have many functions
    if len(functions) > 5:
      prefix_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
      for func in functions:
        prefix = func["name"].split("_")[0] if "_" in func["name"] else "misc"
        prefix_groups[prefix].append(func)

      # Sort functions by line number to create non-overlapping sections
      all_funcs_sorted = sorted(functions, key=lambda f: f["line"])

      # Find where code starts (after imports and class definitions)
      code_start = 1
      for i, line in enumerate(self.lines, 1):
        stripped = line.strip()
        if stripped and not stripped.startswith(("#", '"', "'", "from ", "import ", "@")):
          # Check if it's not a class definition
          if not stripped.startswith("class "):
            code_start = i
            break

      # Create sections by grouping consecutive functions with same prefix
      sections = []
      current_prefix = None
      current_start = code_start
      current_end = code_start

      for func in all_funcs_sorted:
        prefix = func["name"].split("_")[0] if "_" in func["name"] else "misc"

        if current_prefix is None:
          current_prefix = prefix
          current_start = func["line"]
          current_end = func["end_line"]
        elif prefix == current_prefix:
          # Extend current section
          current_end = func["end_line"]
        else:
          # Start new section
          sections.append(
            {
              "name": f"{current_prefix}_functions",
              "start": current_start,
              "end": current_end,
            }  # type: ignore[dict-item]
          )
          current_prefix = prefix
          current_start = func["line"]
          current_end = func["end_line"]

      # Add final section
      if current_prefix:
        sections.append(
          {
            "name": f"{current_prefix}_functions",
            "start": current_start,
            "end": current_end,
          }  # type: ignore[dict-item]
        )

      return sections

    # Fallback: single section
    return [
      {
        "name": "main",
        "start": 1,
        "end": len(self.lines),
      }
    ]

  def suggest_split(self) -> dict[str, Any]:
    """Suggest how to split the file."""
    suggestions: dict[str, Any] = {
      "file": str(self.file_path.relative_to(ROOT)),
      "total_lines": self.total_lines,
      "code_lines": self.code_lines,
      "classes": len(self.get_classes()),
      "functions": len(self.get_functions()),
      "suggestions": [],
    }

    classes = self.get_classes()
    functions = self.get_functions()
    sections = self.get_sections()

    # Suggestion 1: Split by classes
    if len(classes) > 1:
      suggestions["suggestions"].append(
        {
          "type": "split_by_classes",
          "description": f"Split into {len(classes)} files, one per class",
          "files": [f"{self.file_path.stem}_{cls['name'].lower()}.py" for cls in classes],
        }
      )

    # Suggestion 2: Split by logical sections
    if len(sections) > 3:
      suggestions["suggestions"].append(
        {
          "type": "split_by_sections",
          "description": f"Split into {len(sections)} files based on logical sections",
          "sections": [s["name"] for s in sections[:5]],  # Show first 5
        }
      )

    # Suggestion 3: Split handlers/tools into separate modules
    if "handlers" in str(self.file_path) or "tools" in str(self.file_path):
      if len(functions) > 5:
        suggestions["suggestions"].append(
          {
            "type": "split_handlers",
            "description": "Split handlers/tools into separate files in a subdirectory",
            "recommendation": f"Create {self.file_path.parent}/handlers/ or {self.file_path.parent}/tools/",
          }
        )

    # Suggestion 4: Extract constants/helpers
    if self._has_constants():
      suggestions["suggestions"].append(
        {
          "type": "extract_constants",
          "description": "Extract constants and configuration to a separate file",
          "recommendation": f"Create {self.file_path.parent}/constants.py or {self.file_path.parent}/helpers.py",
        }
      )

    return suggestions

  def _has_constants(self) -> bool:
    """Check if file has module-level constants."""
    if not self.tree:
      return False
    for node in self.tree.body:
      if isinstance(node, ast.Assign):
        for target in node.targets:
          if isinstance(target, ast.Name) and target.id.isupper():
            return True
    return False


def find_python_files(root: Path, exclude_dirs: set[str] | None = None) -> list[Path]:
  """Find all Python files in the repository."""
  if exclude_dirs is None:
    exclude_dirs = {".git", ".venv", "venv", "__pycache__", ".ruff_cache", ".mypy_cache"}

  python_files = []
  for path in root.rglob("*.py"):
    # Skip excluded directories
    if any(excluded in path.parts for excluded in exclude_dirs):
      continue
    python_files.append(path)

  return python_files


def analyze_files(threshold: int = 500, top_n: int | None = None) -> list[dict[str, Any]]:
  """Analyze all Python files and return those exceeding threshold."""
  files = find_python_files(ROOT)
  results = []

  for file_path in files:
    try:
      analyzer = FileAnalyzer(file_path)
      if analyzer.total_lines >= threshold:
        results.append(analyzer.suggest_split())
    except Exception as e:
      print(f"Error analyzing {file_path}: {e}", file=sys.stderr)

  # Sort by line count descending
  results.sort(key=lambda x: x["total_lines"], reverse=True)

  if top_n:
    results = results[:top_n]

  return results


def print_report(results: list[dict[str, Any]]) -> None:
  """Print a formatted report."""
  if not results:
    print("✅ No files exceed the threshold!")
    return

  print(f"\n📊 Found {len(results)} files exceeding threshold:\n")
  print("=" * 80)

  for i, result in enumerate(results, 1):
    print(f"\n{i}. {result['file']}")
    print(f"   Lines: {result['total_lines']} total, {result['code_lines']} code")
    print(f"   Classes: {result['classes']}, Functions: {result['functions']}")

    if result["suggestions"]:
      print("\n   💡 Split Suggestions:")
      for suggestion in result["suggestions"]:
        print(f"      • {suggestion['type']}: {suggestion['description']}")
        if "files" in suggestion:
          print(f"        Files: {', '.join(suggestion['files'][:3])}...")
        if "recommendation" in suggestion:
          print(f"        {suggestion['recommendation']}")
    else:
      print("   ⚠️  No automatic split suggestions available")

    print()

  print("=" * 80)
  print("\n💡 To auto-split files, run with --split flag (use with caution!)")
