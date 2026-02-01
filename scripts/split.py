#!/usr/bin/env python3
"""
File splitting utilities.

Provides functionality to split large Python files into smaller modules.
"""

from __future__ import annotations

import re
from pathlib import Path

from .analyze import FileAnalyzer


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
      new_file = self.file_path if i == 0 else output_dir / f"{module_name}_{section_name}.py"

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

    for _i, cls in enumerate(classes):
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
            f"  Function prefixes: { {f['name'].split('_')[0] if '_' in f['name'] else 'misc' for f in functions} }"
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
