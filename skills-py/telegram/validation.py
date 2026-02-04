"""
Input validation helpers for Telegram tool arguments.

Ported from validation.ts.
"""

from __future__ import annotations

import re
from typing import Any


class ValidationError(Exception):
  pass


def validate_id(value: Any, param_name: str) -> int | str:
  """Validate chat_id or user_id — supports integer IDs, string IDs, and usernames."""
  if isinstance(value, (int, float)):
    iv = int(value)
    if iv < -(2**63) or iv > 2**63 - 1:
      raise ValidationError(f"Invalid {param_name}: {value}. ID is out of the valid integer range.")
    return iv

  if isinstance(value, str):
    try:
      iv = int(value)
      if iv < -(2**63) or iv > 2**63 - 1:
        raise ValidationError(
          f"Invalid {param_name}: {value}. ID is out of the valid integer range."
        )
      return iv
    except ValueError:
      pass

    if re.match(r"^@?[a-zA-Z0-9_]{5,}$", value):
      return value if value.startswith("@") else f"@{value}"

    raise ValidationError(
      f"Invalid {param_name}: '{value}'. Must be a valid integer ID or a username string."
    )

  raise ValidationError(f"Invalid {param_name}: {value}. Type must be an integer or a string.")


def validate_positive_int(value: Any, param_name: str) -> int:
  """Validate a positive integer parameter."""
  if isinstance(value, (int, float)):
    iv = int(value)
    if iv <= 0:
      raise ValidationError(f"Invalid {param_name}: {value}. Must be a positive integer.")
    return iv

  if isinstance(value, str):
    try:
      iv = int(value)
    except ValueError:
      raise ValidationError(f"Invalid {param_name}: '{value}'. Must be a positive integer.")
    if iv <= 0:
      raise ValidationError(f"Invalid {param_name}: '{value}'. Must be a positive integer.")
    return iv

  raise ValidationError(f"Invalid {param_name}: {value}. Must be a positive integer.")


def validate_optional_id(value: Any, param_name: str) -> int | str | None:
  """Validate optional ID (can be None)."""
  if value is None:
    return None
  return validate_id(value, param_name)


def opt_number(args: dict[str, Any], key: str, fallback: int) -> int:
  """Read an optional number from args with a fallback."""
  v = args.get(key)
  if isinstance(v, (int, float)):
    return int(v)
  return fallback


def opt_string(args: dict[str, Any], key: str) -> str | None:
  """Read an optional string from args."""
  v = args.get(key)
  return v if isinstance(v, str) else None


def req_string(args: dict[str, Any], key: str) -> str:
  """Read a required string from args."""
  v = args.get(key)
  if not isinstance(v, str) or not v:
    raise ValidationError(f"Missing required parameter: {key}")
  return v


def opt_boolean(args: dict[str, Any], key: str, fallback: bool = False) -> bool:
  """Read an optional boolean from args."""
  v = args.get(key)
  return v if isinstance(v, bool) else fallback
