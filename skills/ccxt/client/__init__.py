"""
CCXT client wrapper for managing multiple exchange connections.
"""

from .ccxt_client import (
  CcxtManager,
  create_ccxt_manager,
  get_ccxt_manager,
)

__all__ = [
  "CcxtManager",
  "create_ccxt_manager",
  "get_ccxt_manager",
]
