"""
CCXT skill setup flow — multi-exchange connection management.

Steps:
  1. exchange_list — View/add/remove exchanges
  2. exchange_add — Add a new exchange (exchange name, API keys, etc.)
  3. exchange_remove — Remove an existing exchange

The setup allows managing multiple exchange connections simultaneously.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from dev.types.setup_types import (
  SetupField,
  SetupFieldError,
  SetupFieldOption,
  SetupResult,
  SetupStep,
)

log = logging.getLogger("skill.ccxt.setup")

# ---------------------------------------------------------------------------
# Module-level transient state
# ---------------------------------------------------------------------------

_exchanges: list[dict[str, Any]] = []


def _reset_state() -> None:
  global _exchanges
  _exchanges = []


async def _load_existing_exchanges(ctx: Any) -> list[dict[str, Any]]:
  """Load existing exchanges from config."""
  try:
    raw = await ctx.read_data("config.json")
    if raw:
      config: dict[str, Any] = json.loads(raw)
      exchanges = config.get("exchanges", [])
      if isinstance(exchanges, list):
        return exchanges
      return []
  except Exception:
    pass
  return []


# ---------------------------------------------------------------------------
# Step definitions
# ---------------------------------------------------------------------------


def _make_exchange_list_step(exchanges: list[dict[str, Any]]) -> SetupStep:
  """Build the exchange list step."""
  if not exchanges:
    return SetupStep(
      id="exchange_list",
      title="Exchange Connections",
      description="No exchanges configured. Add your first exchange to get started.",
      fields=[
        SetupField(
          name="action",
          type="select",
          label="Action",
          description="What would you like to do?",
          required=True,
          options=[
            SetupFieldOption(value="add", label="Add Exchange"),
            SetupFieldOption(value="done", label="Done (Skip for now)"),
          ],
        ),
      ],
    )

  # Build exchange list display
  exchange_options = [
    SetupFieldOption(value="add", label="Add Another Exchange"),
    SetupFieldOption(value="done", label="Done"),
  ]
  for exc in exchanges:
    exc_id = exc.get("exchange_id", "unknown")
    exc_name = exc.get("exchange_name", "unknown")
    sandbox = exc.get("sandbox", False)
    label = f"{exc_name} ({exc_id})" + (" [Sandbox]" if sandbox else "")
    exchange_options.append(SetupFieldOption(value=f"remove:{exc_id}", label=f"Remove: {label}"))

  return SetupStep(
    id="exchange_list",
    title="Exchange Connections",
    description=f"You have {len(exchanges)} exchange(s) configured. Manage your connections:",
    fields=[
      SetupField(
        name="action",
        type="select",
        label="Action",
        description="Select an action",
        required=True,
        options=exchange_options,
      ),
    ],
  )


STEP_ADD_EXCHANGE = SetupStep(
  id="exchange_add",
  title="Add Exchange",
  description="Configure a new exchange connection. You'll need API keys from the exchange.",
  fields=[
    SetupField(
      name="exchange_id",
      type="text",
      label="Connection ID",
      description="Unique identifier for this exchange connection (e.g., 'binance_main', 'coinbase_prod')",
      required=True,
      placeholder="binance_main",
    ),
    SetupField(
      name="exchange_name",
      type="text",
      label="Exchange Name",
      description="CCXT exchange name (e.g., 'binance', 'coinbase', 'kraken')",
      required=True,
      placeholder="binance",
    ),
    SetupField(
      name="api_key",
      type="text",
      label="API Key",
      description="Your exchange API key",
      required=True,
      placeholder="your_api_key",
    ),
    SetupField(
      name="secret",
      type="password",
      label="API Secret",
      description="Your exchange API secret",
      required=True,
    ),
    SetupField(
      name="password",
      type="password",
      label="API Password (Optional)",
      description="Required for some exchanges (e.g., OKX, Bitfinex)",
      required=False,
    ),
    SetupField(
      name="sandbox",
      type="boolean",
      label="Use Sandbox/Testnet",
      description="Enable sandbox/testnet mode for testing",
      required=False,
      default=False,
    ),
    SetupField(
      name="settings",
      type="text",
      label="Exchange Settings (JSON)",
      description='Optional CCXT exchange settings as JSON. Can be an object or array of setting objects. Example: {"defaultType": "spot"} or [{"key": "defaultType", "value": "spot"}]',
      required=False,
      placeholder='{"defaultType": "spot"}',
    ),
  ],
)


# ---------------------------------------------------------------------------
# Hook handlers
# ---------------------------------------------------------------------------


async def on_setup_start(ctx: Any) -> SetupStep:
  """Return the first setup step."""
  _reset_state()
  existing = await _load_existing_exchanges(ctx)
  _exchanges.extend(existing)
  return _make_exchange_list_step(_exchanges)


async def on_setup_submit(ctx: Any, step_id: str, values: dict[str, Any]) -> SetupResult:
  """Validate and process a submitted step."""
  if step_id == "exchange_list":
    return await _handle_exchange_list(ctx, values)
  if step_id == "exchange_add":
    return await _handle_exchange_add(ctx, values)

  return SetupResult(
    status="error",
    errors=[SetupFieldError(field="", message=f"Unknown step: {step_id}")],
  )


async def on_setup_cancel(ctx: Any) -> None:
  """Clean up transient state on cancel."""
  _reset_state()


# ---------------------------------------------------------------------------
# Step handlers
# ---------------------------------------------------------------------------


async def _handle_exchange_list(ctx: Any, values: dict[str, Any]) -> SetupResult:
  global _exchanges

  action = str(values.get("action", "")).strip()

  if action == "done":
    # Save config and complete
    if not _exchanges:
      return SetupResult(
        status="error",
        errors=[
          SetupFieldError(
            field="action",
            message="Please add at least one exchange before completing setup",
          )
        ],
      )

    config = {"exchanges": _exchanges}
    try:
      await ctx.write_data("config.json", json.dumps(config, indent=2))
    except Exception as e:
      log.warning("Failed to save config: %s", e)

    exchange_names = [e.get("exchange_name", "unknown") for e in _exchanges]
    return SetupResult(
      status="complete",
      message=f"Connected to {len(_exchanges)} exchange(s): {', '.join(exchange_names)}",
    )

  if action == "add":
    return SetupResult(status="next", next_step=STEP_ADD_EXCHANGE)

  if action.startswith("remove:"):
    exchange_id = action.replace("remove:", "", 1)
    _exchanges = [e for e in _exchanges if e.get("exchange_id") != exchange_id]
    return SetupResult(
      status="next",
      next_step=_make_exchange_list_step(_exchanges),
    )

  return SetupResult(
    status="error",
    errors=[SetupFieldError(field="action", message="Invalid action")],
  )


async def _handle_exchange_add(ctx: Any, values: dict[str, Any]) -> SetupResult:
  global _exchanges

  errors: list[SetupFieldError] = []

  exchange_id = str(values.get("exchange_id", "")).strip()
  if not exchange_id:
    errors.append(SetupFieldError(field="exchange_id", message="Connection ID is required"))

  exchange_name = str(values.get("exchange_name", "")).strip().lower()
  if not exchange_name:
    errors.append(SetupFieldError(field="exchange_name", message="Exchange name is required"))

  api_key = str(values.get("api_key", "")).strip()
  if not api_key:
    errors.append(SetupFieldError(field="api_key", message="API key is required"))

  secret = str(values.get("secret", ""))
  if not secret:
    errors.append(SetupFieldError(field="secret", message="API secret is required"))

  if errors:
    return SetupResult(status="error", errors=errors)

  # Check if exchange_id already exists
  if any(e.get("exchange_id") == exchange_id for e in _exchanges):
    return SetupResult(
      status="error",
      errors=[
        SetupFieldError(
          field="exchange_id",
          message=f"Connection ID '{exchange_id}' already exists",
        )
      ],
    )

  # Validate exchange name exists in CCXT
  try:
    import ccxt

    if not hasattr(ccxt, exchange_name):
      # Try with proper case
      exchange_class = None
      for name in ccxt.exchanges:
        if name.lower() == exchange_name:
          exchange_class = getattr(ccxt, name, None)
          if exchange_class:
            exchange_name = name
            break

      if not exchange_class:
        return SetupResult(
          status="error",
          errors=[
            SetupFieldError(
              field="exchange_name",
              message=f"Exchange '{exchange_name}' not found in CCXT. Check available exchanges.",
            )
          ],
        )
  except Exception as e:
    log.warning("Failed to validate exchange name: %s", e)
    return SetupResult(
      status="error",
      errors=[
        SetupFieldError(
          field="exchange_name",
          message=f"Failed to validate exchange: {e}",
        )
      ],
    )

  password = str(values.get("password", "")).strip()
  sandbox = bool(values.get("sandbox", False))

  # Parse settings/options
  options: dict[str, Any] = {}
  settings_json = str(values.get("settings", "")).strip()
  if settings_json:
    try:
      settings_data = json.loads(settings_json)
      # Handle array of setting objects: [{"key": "value", ...}, ...]
      if isinstance(settings_data, list):
        # Convert array of objects to a single options dict
        for setting_obj in settings_data:
          if isinstance(setting_obj, dict):
            # If it's an object with "key" and "value", use that structure
            if "key" in setting_obj and "value" in setting_obj:
              options[setting_obj["key"]] = setting_obj["value"]
            else:
              # Otherwise merge all keys from the object
              options.update(setting_obj)
      # Handle single object: {"key": "value", ...}
      elif isinstance(settings_data, dict):
        options = settings_data
      else:
        return SetupResult(
          status="error",
          errors=[
            SetupFieldError(
              field="settings",
              message="Settings must be a JSON object or array of objects",
            )
          ],
        )
    except json.JSONDecodeError as e:
      return SetupResult(
        status="error",
        errors=[
          SetupFieldError(
            field="settings",
            message=f"Invalid JSON in settings: {e}",
          )
        ],
      )

  # Add exchange to list
  exchange_config = {
    "exchange_id": exchange_id,
    "exchange_name": exchange_name,
    "api_key": api_key,
    "secret": secret,
    "password": password,
    "sandbox": sandbox,
    "options": options,
    "settings": settings_json if settings_json else None,  # Store raw JSON for reference
  }

  _exchanges.append(exchange_config)

  return SetupResult(
    status="next",
    next_step=_make_exchange_list_step(_exchanges),
  )
