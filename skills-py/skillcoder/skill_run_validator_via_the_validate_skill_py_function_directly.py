from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dev.security.scan_secrets import scan_content
from dev.types.skill_types import (
  ToolResult,
)
from dev.validate.validator import validate_skill_py

"""Section: Run validator via the validate_skill_py function directly"""


# Run validator via the validate_skill_py function directly
def _run_validator(skill_py: str, skill_name: str) -> dict[str, Any]:
  """Run validator on skill."""
  result = validate_skill_py(skill_py, skill_name)
  report: dict[str, Any] = {
    "skill": skill_name,
    "errors": result.errors,
    "warnings": result.warnings,
    "passed": len(result.errors) == 0,
  }

  # Also run security scan

  skill_dir = Path(f"skills/{skill_name}")
  py_files = list(skill_dir.glob("*.py"))
  findings_list: list[dict[str, Any]] = []
  for pf in py_files:
    content = pf.read_text(encoding="utf-8")
    rel = f"skills/{skill_name}/{pf.name}"
    findings = scan_content(content, rel)
    for f in findings:
      findings_list.append(
        {
          "file": f.file,
          "line": f.line,
          "severity": f.severity,
          "pattern": f.pattern,
          "description": f.description,
        }
      )

  report["security_findings"] = findings_list
  sec_errors = [f for f in findings_list if f["severity"] == "error"]
  if sec_errors:
    report["passed"] = False

  return ToolResult(content=json.dumps(report, indent=2))
