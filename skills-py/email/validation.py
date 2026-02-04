"""
Input validation helpers for email tool arguments.
"""

from __future__ import annotations

import re
from typing import Any


class ValidationError(Exception):
  pass


def validate_email_address(value: Any, param_name: str) -> str:
  """Validate an email address."""
  if not isinstance(value, str) or not value:
    raise ValidationError(f"Missing required parameter: {param_name}")
  value = value.strip()
  if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value):
    raise ValidationError(f"Invalid email address for {param_name}: {value}")
  # Type narrowing: value is guaranteed to be str at this point
  return str(value)


def validate_email_list(value: Any, param_name: str) -> list[str]:
  """Validate a list of email addresses or a comma-separated string."""
  if isinstance(value, str):
    parts = [p.strip() for p in value.split(",") if p.strip()]
  elif isinstance(value, list):
    parts = [str(p).strip() for p in value if p]
  else:
    raise ValidationError(f"Invalid {param_name}: must be a list or comma-separated string")

  if not parts:
    raise ValidationError(f"Missing required parameter: {param_name}")

  validated = []
  for addr in parts:
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", addr):
      raise ValidationError(f"Invalid email address in {param_name}: {addr}")
    validated.append(addr)
  return validated


def validate_folder(value: Any, param_name: str = "folder") -> str:
  """Validate a folder name."""
  if not isinstance(value, str) or not value.strip():
    raise ValidationError(f"Missing required parameter: {param_name}")
  return value.strip()


def validate_uid(value: Any, param_name: str = "message_id") -> int:
  """Validate a UID (positive integer)."""
  if isinstance(value, (int, float)):
    uid = int(value)
    if uid <= 0:
      raise ValidationError(f"Invalid {param_name}: must be a positive integer")
    return uid
  if isinstance(value, str):
    try:
      uid = int(value)
    except ValueError:
      raise ValidationError(f"Invalid {param_name}: must be a positive integer")
    if uid <= 0:
      raise ValidationError(f"Invalid {param_name}: must be a positive integer")
    return uid
  raise ValidationError(f"Invalid {param_name}: must be a positive integer")


def validate_uid_list(value: Any, param_name: str = "message_ids") -> list[int]:
  """Validate a list of UIDs."""
  if isinstance(value, (int, float)):
    return [int(value)]
  if isinstance(value, str):
    try:
      return [int(value)]
    except ValueError:
      raise ValidationError(f"Invalid {param_name}: must be an integer or list of integers")
  if isinstance(value, list):
    result = []
    for item in value:
      if isinstance(item, (int, float)):
        result.append(int(item))
      elif isinstance(item, str):
        try:
          result.append(int(item))
        except ValueError:
          raise ValidationError(f"Invalid UID in {param_name}: {item}")
      else:
        raise ValidationError(f"Invalid UID in {param_name}: {item}")
    if not result:
      raise ValidationError(f"Missing required parameter: {param_name}")
    return result
  raise ValidationError(f"Invalid {param_name}: must be an integer or list of integers")


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
