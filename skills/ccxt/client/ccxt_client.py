"""
CCXT client wrapper for managing multiple exchange instances.

Supports connecting to multiple exchanges simultaneously, each with its own
API keys and configuration.
"""

from __future__ import annotations

import logging
from typing import Any

import ccxt

log = logging.getLogger("skill.ccxt.client")

_manager: CcxtManager | None = None


class CcxtManager:
  """Manages multiple CCXT exchange instances."""

  def __init__(self) -> None:
    self._exchanges: dict[str, ccxt.Exchange] = {}
    self._configs: dict[str, dict[str, Any]] = {}

  def add_exchange(
    self,
    exchange_id: str,
    exchange_name: str,
    api_key: str = "",
    secret: str = "",
    password: str = "",
    sandbox: bool = False,
    options: dict[str, Any] | None = None,
    settings: list[dict[str, Any]] | None = None,
  ) -> bool:
    """
    Add or update an exchange connection.

    Args:
        exchange_id: Unique identifier for this exchange connection
        exchange_name: CCXT exchange name (e.g., 'binance', 'coinbase')
        api_key: API key
        secret: API secret
        password: API password (for some exchanges)
        sandbox: Use sandbox/testnet mode
        options: Additional exchange-specific options (dict)
        settings: Array of setting objects to merge into options

    Returns:
        True if successful, False otherwise
    """
    try:
      # Get exchange class
      exchange_class = getattr(ccxt, exchange_name.lower(), None)
      if not exchange_class:
        # Try with proper case
        exchange_class = getattr(ccxt, exchange_name, None)
        if not exchange_class:
          log.error("Exchange %s not found in CCXT", exchange_name)
          return False

      # Merge settings array into options if provided
      merged_options = dict(options or {})
      if settings:
        for setting_obj in settings:
          if isinstance(setting_obj, dict):
            # If it's an object with "key" and "value", use that structure
            if "key" in setting_obj and "value" in setting_obj:
              merged_options[setting_obj["key"]] = setting_obj["value"]
            else:
              # Otherwise merge all keys from the object
              merged_options.update(setting_obj)

      # Build config
      config: dict[str, Any] = {
        "apiKey": api_key,
        "secret": secret,
        "enableRateLimit": True,
        "options": merged_options,
      }

      if password:
        config["password"] = password

      if sandbox:
        config["sandbox"] = True

      # Create exchange instance
      exchange = exchange_class(config)

      # Test connection (optional - just check if exchange is available)
      if not hasattr(exchange, "load_markets"):
        log.error("Exchange %s does not support load_markets", exchange_name)
        return False

      # Store exchange and config
      self._exchanges[exchange_id] = exchange
      self._configs[exchange_id] = {
        "exchange_id": exchange_id,
        "exchange_name": exchange_name,
        "api_key": api_key,
        "secret": secret,
        "password": password,
        "sandbox": sandbox,
        "options": merged_options,
        "settings": settings,  # Store raw settings array if provided
      }

      log.info("Added exchange %s (%s)", exchange_id, exchange_name)
      return True

    except Exception as e:
      log.exception("Failed to add exchange %s: %s", exchange_id, e)
      return False

  def remove_exchange(self, exchange_id: str) -> bool:
    """Remove an exchange connection."""
    if exchange_id in self._exchanges:
      del self._exchanges[exchange_id]
      del self._configs[exchange_id]
      log.info("Removed exchange %s", exchange_id)
      return True
    return False

  def get_exchange(self, exchange_id: str) -> ccxt.Exchange | None:
    """Get an exchange instance by ID."""
    return self._exchanges.get(exchange_id)

  def list_exchanges(self) -> list[dict[str, Any]]:
    """List all configured exchanges."""
    return [
      {
        "exchange_id": config["exchange_id"],
        "exchange_name": config["exchange_name"],
        "sandbox": config.get("sandbox", False),
      }
      for config in self._configs.values()
    ]

  def get_config(self, exchange_id: str) -> dict[str, Any] | None:
    """Get configuration for an exchange."""
    return self._configs.get(exchange_id)

  def has_exchange(self, exchange_id: str) -> bool:
    """Check if an exchange is configured."""
    return exchange_id in self._exchanges

  def get_available_exchanges(self) -> list[str]:
    """Get list of all available CCXT exchange names."""
    return sorted(ccxt.exchanges)


def create_ccxt_manager() -> CcxtManager:
  """Create a new CCXT manager instance."""
  return CcxtManager()


def get_ccxt_manager() -> CcxtManager | None:
  """Get the global CCXT manager instance."""
  return _manager


def set_ccxt_manager(manager: CcxtManager) -> None:
  """Set the global CCXT manager instance."""
  global _manager
  _manager = manager
