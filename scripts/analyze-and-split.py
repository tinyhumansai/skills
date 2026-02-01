#!/usr/bin/env python3
"""
Analyze Python files by line count and suggest/perform splits.

Finds files exceeding a threshold (default 300 lines) and provides
suggestions for splitting them into smaller modules.

Usage:
    python scripts/analyze-and-split.py                    # Analyze and report
    python scripts/analyze-and-split.py --threshold 500   # Custom threshold
    python scripts/analyze-and-split.py --split            # Auto-split files
    python scripts/analyze-and-split.py --top 10           # Show top N files
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# File Analysis
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# File Splitting
# ---------------------------------------------------------------------------


class FileSplitter:
  """Split a large Python file into smaller modules."""

  def __init__(self, file_path: Path):
    self.file_path = file_path
    self.analyzer = FileAnalyzer(file_path)
    self.content = self.analyzer.content
    self.lines = self.analyzer.lines

  def split_by_sections(self, output_dir: Path | None = None) -> list[Path]:
    """Split file by logical sections (comment headers, classes, functions)."""
    if output_dir is None:
      output_dir = self.file_path.parent

    sections = self.analyzer.get_sections()
    if len(sections) < 2:
      raise ValueError("File has fewer than 2 sections, cannot split")

    created_files = []
    imports = self._extract_imports()
    module_name = self.file_path.stem

    for i, section in enumerate(sections):
      # Generate filename
      section_name = self._sanitize_section_name(section["name"])
      if i == 0:
        # First section goes to main file
        new_file = self.file_path
      else:
        new_file = output_dir / f"{module_name}_{section_name}.py"

      # Extract section content
      start_line = section["start"] - 1  # Convert to 0-based
      end_line = section["end"]
      section_lines = self.lines[start_line:end_line]

      # Build file content
      file_content = []
      if i > 0:  # Add imports to new files
        file_content.extend(imports)
        file_content.append("")
        file_content.append(f'"""Section: {section["name"]}"""')
        file_content.append("")

      file_content.extend(section_lines)

      # Write file
      if i == 0:
        # Update original file with first section
        new_file.write_text("\n".join(file_content) + "\n", encoding="utf-8")
      else:
        new_file.write_text("\n".join(file_content) + "\n", encoding="utf-8")
        created_files.append(new_file)

    return created_files

  def split_by_classes(self, output_dir: Path | None = None) -> list[Path]:
    """Split file by class definitions."""
    if output_dir is None:
      output_dir = self.file_path.parent

    classes = self.analyzer.get_classes()
    if len(classes) < 2:
      raise ValueError("File has fewer than 2 classes, cannot split")

    created_files = []
    imports = self._extract_imports()
    module_name = self.file_path.stem

    # Find all non-class content (imports, module-level code)
    non_class_lines = []
    class_ranges = [(cls["line"] - 1, cls["end_line"]) for cls in classes]

    for i, line in enumerate(self.lines):
      in_class = any(start <= i < end for start, end in class_ranges)
      if not in_class:
        non_class_lines.append((i, line))

    for i, cls in enumerate(classes):
      # Generate filename
      class_file = output_dir / f"{module_name}_{cls['name'].lower()}.py"

      # Build file content
      file_content = []
      file_content.extend(imports)
      file_content.append("")
      file_content.append(f'"""Class: {cls["name"]}"""')
      file_content.append("")

      # Add class definition
      start_line = cls["line"] - 1
      end_line = cls["end_line"]
      file_content.extend(self.lines[start_line:end_line])

      # Write file
      class_file.write_text("\n".join(file_content) + "\n", encoding="utf-8")
      created_files.append(class_file)

    # Update original file to import from new modules
    if non_class_lines:
      main_content = []
      main_content.extend(imports)
      main_content.append("")
      for cls in classes:
        module_ref = f"{module_name}_{cls['name'].lower()}"
        main_content.append(f"from .{module_ref} import {cls['name']}")
      main_content.append("")
      main_content.extend([line for _, line in non_class_lines])

      self.file_path.write_text("\n".join(main_content) + "\n", encoding="utf-8")

    return created_files

  def _extract_imports(self) -> list[str]:
    """Extract import statements from the file."""
    imports = []
    in_docstring = False
    docstring_char = None

    for line in self.lines:
      stripped = line.strip()

      # Track docstrings
      if stripped.startswith('"""') or stripped.startswith("'''"):
        if not in_docstring:
          in_docstring = True
          docstring_char = stripped[0:3]
        elif docstring_char and stripped.endswith(docstring_char):
          in_docstring = False
        continue

      if in_docstring:
        continue

      # Collect imports
      if stripped.startswith(("import ", "from ")):
        imports.append(line.rstrip())

    return imports

  def _sanitize_section_name(self, name: str) -> str:
    """Convert section name to valid filename."""
    # Remove "Class:" or "Function:" prefix
    name = re.sub(r"^(Class|Function):\s*", "", name)
    # Remove special characters
    name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    # Convert to lowercase
    name = name.lower()
    # Remove multiple underscores
    name = re.sub(r"_+", "_", name)
    # Remove leading/trailing underscores
    name = name.strip("_")
    return name or "section"


# ---------------------------------------------------------------------------
# Main Analysis
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def split_file(
  file_path: Path, method: str = "sections", dry_run: bool = False, verbose: bool = False
) -> list[Path]:
  """Split a file using the specified method."""
  splitter = FileSplitter(file_path)

  if method == "sections":
    if dry_run:
      sections = splitter.analyzer.get_sections()
      functions = splitter.analyzer.get_functions()
      classes = splitter.analyzer.get_classes()

      if verbose:
        print(f"\nAnalysis for {file_path}:")
        print(f"  Total lines: {splitter.analyzer.total_lines}")
        print(f"  Functions: {len(functions)}")
        print(f"  Classes: {len(classes)}")
        if functions:
          print(
            f"  Function prefixes: {set(f['name'].split('_')[0] if '_' in f['name'] else 'misc' for f in functions)}"
          )

      print(f"\nWould split {file_path} into {len(sections)} files:")
      for i, section in enumerate(sections[:10]):
        print(f"  {i + 1}. {section['name']} (lines {section['start']}-{section['end']})")
      if len(sections) > 10:
        print(f"  ... and {len(sections) - 10} more sections")
      return []
    return splitter.split_by_sections()
  elif method == "classes":
    if dry_run:
      classes = splitter.analyzer.get_classes()
      print(f"Would split {file_path} into {len(classes)} files:")
      for cls in classes:
        print(f"  - {cls['name']} (lines {cls['line']}-{cls['end_line']})")
      return []
    return splitter.split_by_classes()
  else:
    raise ValueError(f"Unknown split method: {method}")


def main() -> int:
  """Main entry point."""
  parser = argparse.ArgumentParser(
    description="Analyze Python files and suggest splits",
    formatter_class=argparse.RawDescriptionHelpFormatter,
  )
  parser.add_argument(
    "--threshold",
    type=int,
    default=500,
    help="Line count threshold (default: 500)",
  )
  parser.add_argument(
    "--top",
    type=int,
    default=None,
    help="Show only top N files",
  )
  parser.add_argument(
    "--split",
    action="store_true",
    help="Auto-split files by sections",
  )
  parser.add_argument(
    "--split-classes",
    action="store_true",
    help="Auto-split files by classes",
  )
  parser.add_argument(
    "--file",
    type=str,
    default=None,
    help="Split a specific file (relative path)",
  )
  parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Show what would be split without actually splitting",
  )
  parser.add_argument(
    "--verbose",
    action="store_true",
    help="Show detailed analysis",
  )

  args = parser.parse_args()

  # Handle single file split
  if args.file:
    file_path = ROOT / args.file
    if not file_path.exists():
      print(f"Error: File not found: {file_path}", file=sys.stderr)
      return 1

    method = "classes" if args.split_classes else "sections"
    try:
      created = split_file(file_path, method=method, dry_run=args.dry_run, verbose=args.verbose)
      if args.dry_run:
        print("\n💡 Run without --dry-run to perform the split")
      else:
        print(f"\n✅ Split {file_path} into {len(created) + 1} files:")
        print(f"   - {file_path} (updated)")
        for f in created:
          print(f"   - {f}")
    except Exception as e:
      print(f"Error splitting file: {e}", file=sys.stderr)
      import traceback

      if args.verbose:
        traceback.print_exc()
      return 1
    return 0

  # Handle bulk split
  if args.split or args.split_classes:
    results = analyze_files(threshold=args.threshold, top_n=args.top)
    if not results:
      print("No files to split!")
      return 0

    method = "classes" if args.split_classes else "sections"
    print(f"\n⚠️  About to split {len(results)} files using method: {method}")
    if not args.dry_run:
      response = input("Continue? (yes/no): ")
      if response.lower() != "yes":
        print("Cancelled.")
        return 0

    for result in results:
      file_path = ROOT / result["file"]
      try:
        created = split_file(file_path, method=method, dry_run=args.dry_run)
        if not args.dry_run:
          print(f"✅ Split {file_path} into {len(created) + 1} files")
      except Exception as e:
        print(f"❌ Error splitting {file_path}: {e}", file=sys.stderr)

    return 0

  # Default: analyze and report
  results = analyze_files(threshold=args.threshold, top_n=args.top)
  print_report(results)

  return 0


if __name__ == "__main__":
  sys.exit(main())
