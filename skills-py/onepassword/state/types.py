"""
State type definitions.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class OnePasswordState:
  """1Password skill state."""

  is_initialized: bool = False
  connection_status: str = "disconnected"  # disconnected, connected, error
  connection_error: str | None = None
  account: str | None = None
  vault: str | None = None
