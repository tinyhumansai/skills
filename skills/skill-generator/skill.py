"""
Skill Generator — a meta-skill that creates new AlphaHuman skills.

Provides tools for the AI to scaffold, write, validate, test, and
security-scan skills on-the-fly when a user requests a capability
no existing skill covers.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from dev.types.skill_types import (
    SkillDefinition,
    SkillContext,
    SkillHooks,
    SkillOptionDefinition,
    SkillTool,
    ToolDefinition,
    ToolResult,
)

def _import_templates():
    """Import templates module, handling both package and dynamic-import contexts."""
    try:
        from .templates import (
            generate_skill_py,
            generate_main_py,
            generate_init_py,
            generate_manifest_json,
        )
    except ImportError:
        import importlib.util
        _tpl_path = Path(__file__).resolve().parent / "templates.py"
        _spec = importlib.util.spec_from_file_location("_skill_gen_templates", _tpl_path)
        _mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
        _spec.loader.exec_module(_mod)  # type: ignore[union-attr]
        generate_skill_py = _mod.generate_skill_py
        generate_main_py = _mod.generate_main_py
        generate_init_py = _mod.generate_init_py
        generate_manifest_json = _mod.generate_manifest_json
    return generate_skill_py, generate_main_py, generate_init_py, generate_manifest_json


generate_skill_py, generate_main_py, generate_init_py, generate_manifest_json = _import_templates()

log = logging.getLogger("skill.skill-generator")

NAME_PATTERN = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")

# Repo root: skills/skill-generator/../../ => skills repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SKILLS_DIR = _REPO_ROOT / "skills"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_repo_root() -> Path:
    return _REPO_ROOT


def _get_skills_dir() -> Path:
    return _SKILLS_DIR


def _validate_skill_name(name: str) -> str | None:
    """Return an error message if the name is invalid, else None."""
    if not name:
        return "Skill name is required"
    if not NAME_PATTERN.match(name):
        return f'Invalid name "{name}" — must be lowercase letters and hyphens (e.g. "my-skill")'
    if name == "skill-generator":
        return "Cannot overwrite the skill-generator skill itself"
    return None


def _safe_skill_path(name: str) -> Path | None:
    """Return the skill directory path if it's safely contained. None if path traversal."""
    target = (_get_skills_dir() / name).resolve()
    if not str(target).startswith(str(_get_skills_dir().resolve())):
        return None
    return target


def _scan_skill_info(skill_dir: Path) -> dict[str, Any] | None:
    """Extract skill metadata from a skill.py using regex (no dynamic import)."""
    skill_py = skill_dir / "skill.py"
    if not skill_py.exists():
        return None

    content = skill_py.read_text(encoding="utf-8")
    info: dict[str, Any] = {"name": skill_dir.name, "directory": skill_dir.name}

    # Extract name
    m = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
    if m:
        info["name"] = m.group(1)

    # Extract description
    m = re.search(r'description\s*=\s*["\']([^"\']+)["\']', content)
    if m:
        info["description"] = m.group(1)

    # Extract version
    m = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
    if m:
        info["version"] = m.group(1)

    # Count tools by finding SkillTool( occurrences
    tool_count = len(re.findall(r"SkillTool\s*\(", content))
    info["tool_count"] = tool_count

    # Find tool names
    tool_names = re.findall(r'name\s*=\s*["\']([a-z_][a-z0-9_]*)["\']', content)
    # Filter to likely tool names (exclude the skill name itself and common fields)
    info["tool_names"] = [
        n for n in tool_names
        if n != info.get("name") and n not in ("on_load", "on_unload", "on_tick")
    ]

    # Find defined hooks
    hooks_found = []
    for hook in (
        "on_load", "on_unload", "on_session_start", "on_session_end",
        "on_before_message", "on_after_response", "on_tick",
    ):
        if re.search(rf"{hook}\s*=\s*\w", content):
            hooks_found.append(hook)
    info["hooks"] = hooks_found

    return info


# ---------------------------------------------------------------------------
# Tool: list_available_skills
# ---------------------------------------------------------------------------


async def _list_available_skills(args: dict[str, Any]) -> ToolResult:
    """Scan skills/ directory and return installed skills with metadata."""
    try:
        verbose = args.get("verbose", False)
        skills_dir = _get_skills_dir()

        if not skills_dir.is_dir():
            return ToolResult(content="No skills directory found.")

        results: list[dict[str, Any]] = []
        for entry in sorted(skills_dir.iterdir()):
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            info = _scan_skill_info(entry)
            if info:
                if not verbose:
                    info.pop("tool_names", None)
                    info.pop("hooks", None)
                results.append(info)

        return ToolResult(content=json.dumps(results, indent=2))
    except Exception as e:
        return ToolResult(content=f"Error listing skills: {e}", is_error=True)


# ---------------------------------------------------------------------------
# Tool: generate_skill
# ---------------------------------------------------------------------------


async def _generate_skill(args: dict[str, Any]) -> ToolResult:
    """Create a new skill directory with complete skill.py and supporting files."""
    try:
        name = args.get("name", "")
        description = args.get("description", "")
        tool_specs = args.get("tools", [])
        include_tick = args.get("include_tick", False)
        tick_interval_ms = args.get("tick_interval_ms", 60_000)
        include_transforms = args.get("include_transforms", False)
        include_state = args.get("include_state", False)

        # Validate name
        err = _validate_skill_name(name)
        if err:
            return ToolResult(content=err, is_error=True)

        # Check path safety
        target = _safe_skill_path(name)
        if target is None:
            return ToolResult(content="Invalid skill path", is_error=True)

        # Check for conflicts
        if target.exists():
            return ToolResult(
                content=f'Skill directory "{name}" already exists. Use write_skill_file to modify it.',
                is_error=True,
            )

        # Validate tick interval
        if include_tick and tick_interval_ms < 1000:
            return ToolResult(content="tick_interval_ms must be >= 1000", is_error=True)

        # Generate files
        target.mkdir(parents=True, exist_ok=True)

        skill_py = generate_skill_py(
            name,
            description,
            tools=tool_specs,
            include_tick=include_tick,
            tick_interval_ms=tick_interval_ms,
            include_transforms=include_transforms,
            include_state=include_state,
        )
        (target / "skill.py").write_text(skill_py, encoding="utf-8")

        main_py = generate_main_py(name)
        (target / "__main__.py").write_text(main_py, encoding="utf-8")

        init_py = generate_init_py(name)
        (target / "__init__.py").write_text(init_py, encoding="utf-8")

        manifest = generate_manifest_json(
            name,
            description,
            tick_interval_ms=tick_interval_ms if include_tick else None,
        )
        (target / "manifest.json").write_text(manifest, encoding="utf-8")

        files_created = ["skill.py", "__main__.py", "__init__.py", "manifest.json"]
        tool_count = len(tool_specs)

        return ToolResult(
            content=json.dumps({
                "status": "created",
                "skill_name": name,
                "directory": f"skills/{name}",
                "files": files_created,
                "tool_count": tool_count,
            }, indent=2)
        )
    except Exception as e:
        return ToolResult(content=f"Error generating skill: {e}", is_error=True)


# ---------------------------------------------------------------------------
# Tool: write_skill_file
# ---------------------------------------------------------------------------


async def _write_skill_file(args: dict[str, Any]) -> ToolResult:
    """Write or overwrite a file within a skill directory."""
    try:
        skill_name = args.get("skill_name", "")
        filename = args.get("filename", "")
        content = args.get("content", "")

        # Validate skill name
        err = _validate_skill_name(skill_name)
        if err:
            return ToolResult(content=err, is_error=True)

        # Validate filename (no path traversal)
        if not filename or ".." in filename or filename.startswith("/"):
            return ToolResult(content="Invalid filename", is_error=True)

        # Check path safety
        skill_dir = _safe_skill_path(skill_name)
        if skill_dir is None:
            return ToolResult(content="Invalid skill path", is_error=True)

        if not skill_dir.exists():
            return ToolResult(
                content=f'Skill "{skill_name}" does not exist. Use generate_skill first.',
                is_error=True,
            )

        file_path = (skill_dir / filename).resolve()
        # Containment check
        if not str(file_path).startswith(str(skill_dir.resolve())):
            return ToolResult(content="Path traversal detected", is_error=True)

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

        return ToolResult(content=f"Written: skills/{skill_name}/{filename}")
    except Exception as e:
        return ToolResult(content=f"Error writing file: {e}", is_error=True)


# ---------------------------------------------------------------------------
# Tool: validate_skill
# ---------------------------------------------------------------------------


async def _validate_skill(args: dict[str, Any]) -> ToolResult:
    """Validate a skill using the dev validator and security scanner."""
    try:
        skill_name = args.get("skill_name", "")

        err = _validate_skill_name(skill_name)
        if err:
            return ToolResult(content=err, is_error=True)

        skill_dir = _safe_skill_path(skill_name)
        if skill_dir is None or not skill_dir.exists():
            return ToolResult(content=f'Skill "{skill_name}" not found', is_error=True)

        skill_py = skill_dir / "skill.py"
        if not skill_py.exists():
            return ToolResult(content=f'No skill.py in "{skill_name}"', is_error=True)

        # Run validator via the validate_skill_py function directly
        from dev.validate.validator import validate_skill_py, SkillResult as ValidatorResult

        result = validate_skill_py(skill_py, skill_name)
        report: dict[str, Any] = {
            "skill": skill_name,
            "errors": result.errors,
            "warnings": result.warnings,
            "passed": len(result.errors) == 0,
        }

        # Also run security scan
        from dev.security.scan_secrets import scan_content

        py_files = list(skill_dir.glob("*.py"))
        findings_list: list[dict[str, Any]] = []
        for pf in py_files:
            content = pf.read_text(encoding="utf-8")
            rel = f"skills/{skill_name}/{pf.name}"
            findings = scan_content(content, rel)
            for f in findings:
                findings_list.append({
                    "file": f.file,
                    "line": f.line,
                    "severity": f.severity,
                    "pattern": f.pattern,
                    "description": f.description,
                })

        report["security_findings"] = findings_list
        sec_errors = [f for f in findings_list if f["severity"] == "error"]
        if sec_errors:
            report["passed"] = False

        return ToolResult(content=json.dumps(report, indent=2))
    except Exception as e:
        return ToolResult(content=f"Error validating skill: {e}", is_error=True)


# ---------------------------------------------------------------------------
# Tool: test_skill
# ---------------------------------------------------------------------------


async def _test_skill(args: dict[str, Any]) -> ToolResult:
    """Run the test harness on a skill via subprocess."""
    try:
        skill_name = args.get("skill_name", "")
        verbose = args.get("verbose", False)

        err = _validate_skill_name(skill_name)
        if err:
            return ToolResult(content=err, is_error=True)

        skill_dir = _safe_skill_path(skill_name)
        if skill_dir is None or not skill_dir.exists():
            return ToolResult(content=f'Skill "{skill_name}" not found', is_error=True)

        cmd = [sys.executable, "-m", "dev.harness.runner", str(skill_dir)]
        if verbose:
            cmd.append("--verbose")

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(_get_repo_root()),
        )

        output = proc.stdout + proc.stderr
        return ToolResult(
            content=output.strip() or "(no output)",
            is_error=proc.returncode != 0,
        )
    except subprocess.TimeoutExpired:
        return ToolResult(content="Test timed out after 30 seconds", is_error=True)
    except Exception as e:
        return ToolResult(content=f"Error testing skill: {e}", is_error=True)


# ---------------------------------------------------------------------------
# Tool: security_scan_skill
# ---------------------------------------------------------------------------


async def _security_scan_skill(args: dict[str, Any]) -> ToolResult:
    """Run security scanner on all .py files in a skill directory."""
    try:
        skill_name = args.get("skill_name", "")

        err = _validate_skill_name(skill_name)
        if err:
            return ToolResult(content=err, is_error=True)

        skill_dir = _safe_skill_path(skill_name)
        if skill_dir is None or not skill_dir.exists():
            return ToolResult(content=f'Skill "{skill_name}" not found', is_error=True)

        from dev.security.scan_secrets import scan_content

        py_files = list(skill_dir.glob("*.py"))
        if not py_files:
            return ToolResult(content="No Python files found to scan.")

        all_findings: list[dict[str, Any]] = []
        for pf in py_files:
            content = pf.read_text(encoding="utf-8")
            rel = f"skills/{skill_name}/{pf.name}"
            findings = scan_content(content, rel)
            for f in findings:
                all_findings.append({
                    "file": f.file,
                    "line": f.line,
                    "severity": f.severity,
                    "pattern": f.pattern,
                    "description": f.description,
                })

        errors = [f for f in all_findings if f["severity"] == "error"]
        warnings = [f for f in all_findings if f["severity"] == "warning"]

        report = {
            "skill": skill_name,
            "files_scanned": len(py_files),
            "errors": len(errors),
            "warnings": len(warnings),
            "findings": all_findings,
            "clean": len(all_findings) == 0,
        }

        return ToolResult(content=json.dumps(report, indent=2))
    except Exception as e:
        return ToolResult(content=f"Error scanning skill: {e}", is_error=True)


# ---------------------------------------------------------------------------
# Lifecycle hooks
# ---------------------------------------------------------------------------


async def _on_load(ctx: SkillContext) -> None:
    """Load cached skills inventory."""
    ctx.log("skill-generator loaded")
    try:
        raw = await ctx.read_data("skills_cache.json")
        if raw:
            cache = json.loads(raw)
            ctx.set_state({"skills_cache": cache})
    except Exception:
        pass


async def _on_session_start(ctx: SkillContext, session_id: str) -> None:
    """Reset per-session state."""
    state = ctx.get_state() or {}
    state["context_injected"] = False
    state["generation_count"] = 0
    ctx.set_state(state)


async def _on_before_message(ctx: SkillContext, message: str) -> str | None:
    """Inject available skills context on first message of each session."""
    state = ctx.get_state() or {}
    if state.get("context_injected"):
        return None

    # Mark as injected
    state["context_injected"] = True
    ctx.set_state(state)

    # Build compact skills summary
    skills_dir = _get_skills_dir()
    summaries: list[str] = []
    if skills_dir.is_dir():
        for entry in sorted(skills_dir.iterdir()):
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            info = _scan_skill_info(entry)
            if info:
                desc = info.get("description", "")
                tc = info.get("tool_count", 0)
                summaries.append(f"{info['name']} ({tc} tools)")

    if summaries:
        skills_list = ", ".join(summaries)
        context = (
            f"\n[System context: Available skills — {skills_list}. "
            f"If a capability is not covered, use skill-generator tools to create one.]\n"
        )
        return context + message

    return None


async def _on_unload(ctx: SkillContext) -> None:
    """Persist skills cache and generation history."""
    ctx.log("skill-generator unloading")
    state = ctx.get_state() or {}
    cache = state.get("skills_cache")
    if cache:
        try:
            await ctx.write_data("skills_cache.json", json.dumps(cache, indent=2))
        except Exception:
            pass


async def _on_status(ctx: SkillContext) -> dict[str, Any]:
    """Return current skill status information."""
    state = ctx.get_state() or {}
    skills_dir = _get_skills_dir()
    skills_count = 0
    if skills_dir.is_dir():
        skills_count = len([
            e for e in skills_dir.iterdir()
            if e.is_dir() and not e.name.startswith(".")
        ])
    return {
        "ready": True,
        "skills_count": skills_count,
        "generation_count": state.get("generation_count", 0),
    }


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

_TOOLS = [
    SkillTool(
        definition=ToolDefinition(
            name="list_available_skills",
            description="List all installed AlphaHuman skills with names, descriptions, and tool counts.",
            parameters={
                "type": "object",
                "properties": {
                    "verbose": {
                        "type": "boolean",
                        "description": "Include tool names and hook details for each skill.",
                    },
                },
            },
        ),
        execute=_list_available_skills,
    ),
    SkillTool(
        definition=ToolDefinition(
            name="generate_skill",
            description="Generate a new skill with complete skill.py, __main__.py, __init__.py, and manifest.json.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Skill name in lowercase-hyphens (e.g. 'price-tracker').",
                    },
                    "description": {
                        "type": "string",
                        "description": "One-line description of the skill.",
                    },
                    "tools": {
                        "type": "array",
                        "description": "Tool specifications. Each item has: name (string), description (string), parameters (array of {name, type, description, required}).",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "Tool function name (snake_case)."},
                                "description": {"type": "string", "description": "Tool description."},
                                "parameters": {
                                    "type": "array",
                                    "description": "Parameter specs.",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"},
                                            "type": {"type": "string"},
                                            "description": {"type": "string"},
                                            "required": {"type": "boolean"},
                                        },
                                    },
                                },
                            },
                        },
                    },
                    "include_tick": {
                        "type": "boolean",
                        "description": "Include periodic on_tick hook.",
                    },
                    "tick_interval_ms": {
                        "type": "integer",
                        "description": "Tick interval in milliseconds (minimum 1000).",
                    },
                    "include_transforms": {
                        "type": "boolean",
                        "description": "Include on_before_message and on_after_response hooks.",
                    },
                    "include_state": {
                        "type": "boolean",
                        "description": "Include state persistence (on_load reads, on_unload writes state.json).",
                    },
                },
                "required": ["name", "description"],
            },
        ),
        execute=_generate_skill,
    ),
    SkillTool(
        definition=ToolDefinition(
            name="write_skill_file",
            description="Write or overwrite a file within an existing skill directory.",
            parameters={
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "Name of the target skill (must already exist).",
                    },
                    "filename": {
                        "type": "string",
                        "description": "Filename to write (e.g. 'skill.py', 'helpers.py').",
                    },
                    "content": {
                        "type": "string",
                        "description": "File content to write.",
                    },
                },
                "required": ["skill_name", "filename", "content"],
            },
        ),
        execute=_write_skill_file,
    ),
    SkillTool(
        definition=ToolDefinition(
            name="validate_skill",
            description="Validate a skill's structure, types, and security. Returns pass/fail report with errors and warnings.",
            parameters={
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "Name of the skill to validate.",
                    },
                },
                "required": ["skill_name"],
            },
        ),
        execute=_validate_skill,
    ),
    SkillTool(
        definition=ToolDefinition(
            name="test_skill",
            description="Run the test harness on a skill (exercises hooks and tools with mock context). 30s timeout.",
            parameters={
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "Name of the skill to test.",
                    },
                    "verbose": {
                        "type": "boolean",
                        "description": "Include verbose output with stack traces.",
                    },
                },
                "required": ["skill_name"],
            },
        ),
        execute=_test_skill,
    ),
    SkillTool(
        definition=ToolDefinition(
            name="security_scan_skill",
            description="Run security scanner on a skill's Python files. Checks for hardcoded secrets, eval/exec, direct file access, and more.",
            parameters={
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "Name of the skill to scan.",
                    },
                },
                "required": ["skill_name"],
            },
        ),
        execute=_security_scan_skill,
    ),
]


# ---------------------------------------------------------------------------
# Tool-category toggle options
# ---------------------------------------------------------------------------

TOOL_CATEGORY_OPTIONS = [
    SkillOptionDefinition(
        name="enable_generator_tools",
        type="boolean",
        label="Skill Generation",
        description="6 tools — list, generate, write, validate, test, and scan skills",
        default=True,
        group="tool_categories",
        tool_filter=[
            "list_available_skills", "generate_skill", "write_skill_file",
            "validate_skill", "test_skill", "security_scan_skill",
        ],
    ),
]


# ---------------------------------------------------------------------------
# Skill definition
# ---------------------------------------------------------------------------

skill = SkillDefinition(
    name="skill-generator",
    description="Meta-skill that creates, validates, tests, and scans new AlphaHuman skills on-the-fly.",
    version="1.0.0",
    options=TOOL_CATEGORY_OPTIONS,
    hooks=SkillHooks(
        on_load=_on_load,
        on_session_start=_on_session_start,
        on_before_message=_on_before_message,
        on_unload=_on_unload,
        on_status=_on_status,
    ),
    tools=_TOOLS,
)
