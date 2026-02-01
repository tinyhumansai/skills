"""Wallet tool definitions — re-export from parent tools.py."""

from __future__ import annotations

# Import from parent directory's tools.py (avoiding circular import)
import importlib.util
from pathlib import Path

_parent_dir = Path(__file__).parent.parent
_tools_py = _parent_dir / "tools.py"

if _tools_py.exists():
  spec = importlib.util.spec_from_file_location("_wallet_tools", _tools_py)
  if spec and spec.loader:
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    ALL_TOOLS = getattr(module, "ALL_TOOLS", [])
  else:
    ALL_TOOLS = []
else:
  ALL_TOOLS = []

__all__ = ["ALL_TOOLS"]
