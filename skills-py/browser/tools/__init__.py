"""Browser tool definitions — re-export from parent tools.py."""

from __future__ import annotations

# Try to import using absolute import first (works when package is properly set up)
try:
  from skills.browser.tools import ALL_TOOLS
except ImportError:
  # Fallback: import using importlib when package context isn't available
  import importlib.util
  import sys
  from pathlib import Path

  _parent_dir = Path(__file__).parent.parent
  _tools_py = _parent_dir / "tools.py"

  if _tools_py.exists():
    # Add repo root to path for mcp.types and other imports
    repo_root = _parent_dir.parent.parent
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
      sys.path.insert(0, repo_root_str)

    # Load tools.py as part of the skills.browser package
    module_name = "skills.browser.tools"
    spec = importlib.util.spec_from_file_location(module_name, _tools_py)
    if spec and spec.loader:
      _tools_module = importlib.util.module_from_spec(spec)
      # Set package info for relative imports to work
      _tools_module.__package__ = "skills.browser"
      _tools_module.__name__ = module_name
      _tools_module.__file__ = str(_tools_py)

      spec.loader.exec_module(_tools_module)
      ALL_TOOLS = getattr(_tools_module, "ALL_TOOLS", [])
    else:
      ALL_TOOLS = []
  else:
    ALL_TOOLS = []

__all__ = ["ALL_TOOLS"]
