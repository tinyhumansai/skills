"""
Web3 Wallet SkillDefinition — wires setup, tools, and lifecycle hooks
into the unified SkillServer protocol.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from dev.types.skill_types import (
  SkillDefinition,
  SkillHooks,
  SkillTool,
  ToolDefinition,
)
from dev.types.skill_types import (
  ToolResult as SkillToolResult,
)

from .client.wallet_client import WalletClient
from .handlers.wallet_handlers import dispatch_tool, set_wallet_client
from .setup import on_setup_cancel, on_setup_start, on_setup_submit
from .tools import ALL_TOOLS

log = logging.getLogger("skill.wallet.skill")


# ---------------------------------------------------------------------------
# Convert MCP Tool objects → SkillTool objects
# ---------------------------------------------------------------------------


def _make_execute(tool_name: str):
  """Create an async execute function for a given tool name."""

  async def execute(args: dict[str, Any]) -> SkillToolResult:
    result = await dispatch_tool(tool_name, args)
    return SkillToolResult(content=result.content, is_error=result.is_error)

  return execute


def _convert_tools() -> list[SkillTool]:
  """Convert MCP Tool definitions to SkillTool objects."""
  skill_tools: list[SkillTool] = []
  for mcp_tool in ALL_TOOLS:
    schema = mcp_tool.inputSchema if isinstance(mcp_tool.inputSchema, dict) else {}
    definition = ToolDefinition(
      name=mcp_tool.name,
      description=mcp_tool.description or "",
      parameters=schema,
    )
    skill_tools.append(
      SkillTool(
        definition=definition,
        execute=_make_execute(mcp_tool.name),
      )
    )
  return skill_tools


# ---------------------------------------------------------------------------
# Lifecycle hooks
# ---------------------------------------------------------------------------


_wallet_client: WalletClient | None = None


async def _on_load(ctx: Any) -> None:
  """Initialize wallet client from config."""
  global _wallet_client

  # Read config from data dir if it exists
  config: dict[str, Any] = {}
  seed_phrase: str | None = None

  try:
    raw = await ctx.read_data("config.json")
    if raw:
      config = json.loads(raw)
      seed_phrase = config.get("seed_phrase")
      log.info(
        "Loaded config.json: wallets=%d, networks=%d, has_seed=%s",
        len(config.get("wallets", [])),
        len(config.get("networks", [])),
        bool(seed_phrase),
      )
    else:
      log.info("config.json is empty or not found — setup required")
      return
  except Exception as exc:
    log.warning("Failed to read config.json: %s", exc)
    return

  if not seed_phrase:
    log.warning("No seed phrase in config — setup required")
    return

  # Initialize wallet client
  try:
    _wallet_client = WalletClient(config, seed_phrase)
    set_wallet_client(_wallet_client)
    log.info(
      "Wallet client initialized: %d wallets, %d networks",
      len(_wallet_client.wallets),
      len(_wallet_client.networks),
    )
  except Exception as exc:
    log.error("Failed to initialize wallet client: %s", exc)
    _wallet_client = None


async def _on_unload(ctx: Any) -> None:
  """Clean up on unload."""
  global _wallet_client
  _wallet_client = None
  set_wallet_client(None)
  log.info("Wallet skill unloaded")


async def _on_status(ctx: Any) -> dict[str, Any]:
  """Return current skill status."""
  global _wallet_client

  if not _wallet_client:
    return {
      "status": "not_configured",
      "message": "Setup required — no wallet configuration found",
    }

  return {
    "status": "ready",
    "wallets": len(_wallet_client.wallets),
    "networks": len(_wallet_client.networks),
    "wallet_addresses": [w.address for w in _wallet_client.wallets],
  }


# ---------------------------------------------------------------------------
# Skill Definition
# ---------------------------------------------------------------------------

skill = SkillDefinition(
  name="wallet",
  description="Web3 wallet connector — manage EVM and Solana wallets from seed phrases",
  version="1.0.0",
  hooks=SkillHooks(
    on_load=_on_load,
    on_unload=_on_unload,
    on_status=_on_status,
    on_setup_start=on_setup_start,
    on_setup_submit=on_setup_submit,
    on_setup_cancel=on_setup_cancel,
  ),
  tools=_convert_tools(),
  has_setup=True,
  has_disconnect=False,
)
