"""
Security scanner for AlphaHuman skills.

Regex-based pattern scanner that checks skill source files for:
- Hardcoded API keys and secrets
- eval() / exec() usage
- Direct file access outside dataDir
- Network requests (requests, urllib, httpx)
- os.environ access
- subprocess usage

Usage:
    python -m dev.security.scan_secrets [--verbose]
    python -m dev.security.scan_secrets skills/my-skill

Exit code 1 if any errors found.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Console helpers
# ---------------------------------------------------------------------------

PASS = "\033[32m\u2713\033[0m"
FAIL = "\033[31m\u2717\033[0m"
WARN = "\033[33m!\033[0m"


def bold(s: str) -> str:
  return f"\033[1m{s}\033[0m"


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Pattern:
  name: str
  regex: re.Pattern[str]
  severity: str  # "error" | "warning"
  description: str


PATTERNS: list[Pattern] = [
  # --- Secrets / API keys (errors) ---
  Pattern(
    name="bearer-token",
    regex=re.compile(r"""['"`]Bearer\s+[A-Za-z0-9\-._~+/]+=*['"`]""", re.IGNORECASE),
    severity="error",
    description="Hardcoded Bearer token",
  ),
  Pattern(
    name="api-key-hex",
    regex=re.compile(r"""['"`][0-9a-f]{32,64}['"`]""", re.IGNORECASE),
    severity="warning",
    description="Possible hardcoded hex API key (32-64 chars)",
  ),
  Pattern(
    name="api-key-assignment",
    regex=re.compile(
      r"""(?:api[_-]?key|api[_-]?secret|auth[_-]?token|secret[_-]?key|private[_-]?key)\s*[:=]\s*['"`][^'"`]{8,}['"`]""",
      re.IGNORECASE,
    ),
    severity="error",
    description="Hardcoded API key/secret assignment",
  ),
  Pattern(
    name="aws-key",
    regex=re.compile(r"AKIA[0-9A-Z]{16}"),
    severity="error",
    description="AWS access key ID",
  ),
  Pattern(
    name="base64-long",
    regex=re.compile(r"""['"`][A-Za-z0-9+/]{40,}={0,2}['"`]"""),
    severity="warning",
    description="Long base64 string (possible encoded secret)",
  ),
  # --- Dangerous code patterns (errors) ---
  Pattern(
    name="eval",
    regex=re.compile(r"\beval\s*\("),
    severity="error",
    description="eval() usage — arbitrary code execution",
  ),
  Pattern(
    name="exec",
    regex=re.compile(r"\bexec\s*\("),
    severity="error",
    description="exec() usage — arbitrary code execution",
  ),
  # --- File system access (warnings) ---
  Pattern(
    name="open-builtin",
    regex=re.compile(r"\bopen\s*\("),
    severity="warning",
    description="open() call — use ctx.read_data/write_data instead",
  ),
  Pattern(
    name="os-file-ops",
    regex=re.compile(r"\bos\.(?:remove|unlink|rename|mkdir|makedirs|rmdir|listdir)\b"),
    severity="warning",
    description="os file operation — use ctx.read_data/write_data instead",
  ),
  Pattern(
    name="pathlib-write",
    regex=re.compile(r"\.write_text\s*\(|\.write_bytes\s*\("),
    severity="warning",
    description="pathlib write — use ctx.write_data instead",
  ),
  # --- Network access (warnings) ---
  Pattern(
    name="requests-import",
    regex=re.compile(r"\bimport\s+requests\b|\bfrom\s+requests\b"),
    severity="warning",
    description="requests library — skills should not make direct network requests",
  ),
  Pattern(
    name="urllib-import",
    regex=re.compile(r"\bimport\s+urllib\b|\bfrom\s+urllib\b"),
    severity="warning",
    description="urllib usage — skills should not make direct network requests",
  ),
  Pattern(
    name="httpx-import",
    regex=re.compile(r"\bimport\s+httpx\b|\bfrom\s+httpx\b"),
    severity="warning",
    description="httpx library — skills should not make direct network requests",
  ),
  Pattern(
    name="aiohttp-import",
    regex=re.compile(r"\bimport\s+aiohttp\b|\bfrom\s+aiohttp\b"),
    severity="warning",
    description="aiohttp library — skills should not make direct network requests",
  ),
  # --- Environment / subprocess (warnings) ---
  Pattern(
    name="os-environ",
    regex=re.compile(r"\bos\.environ\b"),
    severity="warning",
    description="os.environ access — skills should not read environment variables",
  ),
  Pattern(
    name="subprocess",
    regex=re.compile(r"\bimport\s+subprocess\b|\bfrom\s+subprocess\b|\bsubprocess\."),
    severity="warning",
    description="subprocess usage — skills should not spawn processes",
  ),
]

# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------


@dataclass
class Finding:
  file: str
  line: int
  column: int
  pattern: str
  severity: str
  description: str
  snippet: str


def scan_content(content: str, file_path: str) -> list[Finding]:
  findings: list[Finding] = []
  lines = content.split("\n")

  for pattern in PATTERNS:
    for line_idx, line in enumerate(lines):
      # Skip comments
      trimmed = line.strip()
      if trimmed.startswith("#"):
        continue

      for match in pattern.regex.finditer(line):
        findings.append(
          Finding(
            file=file_path,
            line=line_idx + 1,
            column=match.start() + 1,
            pattern=pattern.name,
            severity=pattern.severity,
            description=pattern.description,
            snippet=trimmed[:100],
          )
        )

  return findings


# ---------------------------------------------------------------------------
# Directory scanning
# ---------------------------------------------------------------------------


def find_skill_files(base_dir: Path) -> list[Path]:
  """Find skill.py files in subdirectories of base_dir."""
  files: list[Path] = []
  if not base_dir.is_dir():
    return files
  for entry in sorted(base_dir.iterdir()):
    if not entry.is_dir() or entry.name.startswith("."):
      continue
    skill_py = entry / "skill.py"
    if skill_py.exists():
      files.append(skill_py)
  return files


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
  args = sys.argv[1:]
  verbose = "--verbose" in args
  specific_dir = next((a for a in args if not a.startswith("--")), None)
  dev_dir = Path(__file__).resolve().parent.parent
  root_dir = dev_dir.parent

  print()
  print(bold("AlphaHuman Skills Security Scanner"))
  print()

  files: list[Path]

  if specific_dir:
    abs_dir = Path(specific_dir).resolve()
    files = []
    skill_py = abs_dir / "skill.py"
    if skill_py.exists():
      files.append(skill_py)
    if not files:
      print("  No scannable files found in the specified directory.")
      sys.exit(0)
  else:
    files = [
      *find_skill_files(root_dir / "skills"),
      *find_skill_files(root_dir / "examples"),
    ]
    # Also scan nested example dirs
    examples_dir = root_dir / "examples"
    if examples_dir.is_dir():
      for cat in sorted(examples_dir.iterdir()):
        if cat.is_dir() and not cat.name.startswith("."):
          files.extend(find_skill_files(cat))

  # Deduplicate
  seen: set[Path] = set()
  unique_files: list[Path] = []
  for f in files:
    resolved = f.resolve()
    if resolved not in seen:
      seen.add(resolved)
      unique_files.append(f)
  files = unique_files

  print(f"  Scanning {len(files)} file(s)...")
  print()

  total_errors = 0
  total_warnings = 0

  for file_path in files:
    content = file_path.read_text(encoding="utf-8")
    rel_path = str(file_path.relative_to(root_dir))
    findings = scan_content(content, rel_path)

    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warning"]

    if not findings:
      print(f"  {PASS} {rel_path}: clean")
    else:
      icon = FAIL if errors else WARN
      print(f"  {icon} {rel_path}:")
      for f in findings:
        f_icon = FAIL if f.severity == "error" else WARN
        print(f"    {f_icon} L{f.line}:{f.column} [{f.pattern}] {f.description}")
        if verbose:
          print(f"      {f.snippet}")

    total_errors += len(errors)
    total_warnings += len(warnings)

  print()
  print(bold("Summary"))
  print(f"  Files scanned: {len(files)}")
  print(f"  {FAIL} Errors:   {total_errors}")
  print(f"  {WARN} Warnings: {total_warnings}")
  print()

  if total_errors > 0:
    print("  Errors must be resolved before merging.")
    print()

  sys.exit(1 if total_errors > 0 else 0)


if __name__ == "__main__":
  main()
