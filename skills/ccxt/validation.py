"""
Input validation helpers for CCXT tool arguments.
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


def opt_number(args: dict[str, Any], key: str, fallback: int | float) -> int | float:
  """Read an optional number from args with a fallback."""
  v = args.get(key)
  if isinstance(v, (int, float)):
    return v
  return fallback


def opt_string_list(args: dict[str, Any], key: str) -> list[str] | None:
  """Read an optional list of strings from args."""
  v = args.get(key)
  if v is None:
    return None
  if isinstance(v, str):
    return [p.strip() for p in v.split(",") if p.strip()]
  if isinstance(v, list):
    return [str(p).strip() for p in v if p]
  return None


def opt_list(args: dict[str, Any], key: str) -> list[Any] | None:
  """Read an optional list from args."""
  v = args.get(key)
  if v is None:
    return None
  if isinstance(v, list):
    return v
  return None


def req_list(args: dict[str, Any], key: str) -> list[Any]:
  """Read a required list from args."""
  v = args.get(key)
  if not isinstance(v, list):
    raise ValidationError(f"Missing required parameter: {key} (must be a list)")
  if not v:
    raise ValidationError(f"Parameter {key} cannot be empty")
  return v
