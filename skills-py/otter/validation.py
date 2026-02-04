"""
Input validation helpers for Otter.ai tool arguments.
"""

from __future__ import annotations

from typing import Any


class ValidationError(Exception):
  pass


def req_string(args: dict[str, Any], key: str) -> str:
  """Read a required string from args."""
  v = args.get(key)
  if not isinstance(v, str) or not v:
    raise ValidationError(f"Missing required parameter: {key}")
  return v


def opt_string(args: dict[str, Any], key: str) -> str | None:
  """Read an optional string from args."""
  v = args.get(key)
  return v if isinstance(v, str) else None


def opt_number(args: dict[str, Any], key: str, fallback: int) -> int:
  """Read an optional number from args with a fallback."""
  v = args.get(key)
  if isinstance(v, (int, float)):
    return int(v)
  return fallback


def opt_boolean(args: dict[str, Any], key: str, fallback: bool = False) -> bool:
  """Read an optional boolean from args."""
  v = args.get(key)
  return v if isinstance(v, bool) else fallback
