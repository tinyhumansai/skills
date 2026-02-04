"""
Input validation helpers.
"""

from __future__ import annotations


class ValidationError(Exception):
  """Raised when input validation fails."""

  pass


def opt_string(args: dict, key: str, default: str | None = None) -> str | None:
  """Extract optional string from args."""
  val = args.get(key)
  if val is None:
    return default
  if isinstance(val, str):
    return val.strip() if val.strip() else default
  return str(val).strip() if str(val).strip() else default


def opt_bool(args: dict, key: str, default: bool | None = None) -> bool | None:
  """Extract optional boolean from args."""
  val = args.get(key)
  if val is None:
    return default
  if isinstance(val, bool):
    return val
  if isinstance(val, str):
    return val.lower() in ("true", "1", "yes", "on")
  return bool(val)


def require_string(args: dict, key: str) -> str:
  """Extract required string from args."""
  val = opt_string(args, key)
  if val is None or val == "":
    raise ValidationError(f"Missing required parameter: {key}")
  return val
