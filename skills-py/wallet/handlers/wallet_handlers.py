"""
Tool handlers for wallet operations.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from dev.types.skill_types import ToolResult

log = logging.getLogger("skill.wallet.handlers")

# Global wallet client (set during on_load)
_wallet_client: Any = None


def set_wallet_client(client: Any) -> None:
  """Set the global wallet client."""
  global _wallet_client
  _wallet_client = client


async def dispatch_tool(tool_name: str, args: dict[str, Any]) -> ToolResult:
  """Dispatch tool calls to appropriate handlers."""
  global _wallet_client

  if not _wallet_client:
    return ToolResult(
      content="Wallet not initialized. Please complete setup first.",
      is_error=True,
    )

  try:
    if tool_name == "list_wallets":
      return await handle_list_wallets()
    elif tool_name == "list_networks":
      return await handle_list_networks()
    elif tool_name == "get_balance":
      return await handle_get_balance(args)
    elif tool_name == "send_transaction":
      return await handle_send_transaction(args)
    elif tool_name == "sign_message":
      return await handle_sign_message(args)
    else:
      return ToolResult(
        content=f"Unknown tool: {tool_name}",
        is_error=True,
      )
  except Exception as exc:
    log.exception("Tool execution failed: %s", exc)
    return ToolResult(
      content=f"Error: {exc!s}",
      is_error=True,
    )


async def handle_list_wallets() -> ToolResult:
  """List all configured wallets."""
  wallets_data = []
  for wallet in _wallet_client.wallets:
    wallets_data.append(
      {
        "index": wallet.index,
        "chain_type": wallet.chain_type,
        "address": wallet.address,
        "label": wallet.label,
      }
    )
  return ToolResult(content=json.dumps({"wallets": wallets_data}, indent=2))


async def handle_list_networks() -> ToolResult:
  """List all configured networks."""
  networks_data = []
  for network in _wallet_client.networks:
    networks_data.append(
      {
        "chain_id": network.chain_id,
        "name": network.name,
        "rpc_url": network.rpc_url,
        "chain_type": network.chain_type,
        "connected": network.is_connected(),
      }
    )
  return ToolResult(content=json.dumps({"networks": networks_data}, indent=2))


async def handle_get_balance(args: dict[str, Any]) -> ToolResult:
  """Get balance for a wallet address on a network."""
  address = args.get("address")
  chain_id = args.get("chain_id")
  chain_type = args.get("chain_type", "evm")

  if not address:
    return ToolResult(content="Missing required parameter: address", is_error=True)
  if not chain_id:
    return ToolResult(content="Missing required parameter: chain_id", is_error=True)

  try:
    balance = await _wallet_client.get_balance(address, chain_id, chain_type)
    return ToolResult(content=json.dumps(balance, indent=2))
  except Exception as exc:
    return ToolResult(content=f"Failed to get balance: {exc}", is_error=True)


async def handle_send_transaction(args: dict[str, Any]) -> ToolResult:
  """Send a transaction."""
  from_address = args.get("from_address")
  to_address = args.get("to_address")
  amount = args.get("amount")
  chain_id = args.get("chain_id")
  chain_type = args.get("chain_type", "evm")
  gas_limit = args.get("gas_limit")

  if not from_address:
    return ToolResult(content="Missing required parameter: from_address", is_error=True)
  if not to_address:
    return ToolResult(content="Missing required parameter: to_address", is_error=True)
  if not amount:
    return ToolResult(content="Missing required parameter: amount", is_error=True)
  if not chain_id:
    return ToolResult(content="Missing required parameter: chain_id", is_error=True)

  try:
    result = await _wallet_client.send_transaction(
      from_address, to_address, amount, chain_id, chain_type, gas_limit
    )
    return ToolResult(content=json.dumps(result, indent=2))
  except Exception as exc:
    return ToolResult(content=f"Failed to send transaction: {exc}", is_error=True)


async def handle_sign_message(args: dict[str, Any]) -> ToolResult:
  """Sign a message with a wallet."""
  address = args.get("address")
  message = args.get("message")
  chain_type = args.get("chain_type", "evm")

  if not address:
    return ToolResult(content="Missing required parameter: address", is_error=True)
  if not message:
    return ToolResult(content="Missing required parameter: message", is_error=True)

  wallet = _wallet_client.get_wallet(address)
  if not wallet:
    return ToolResult(content=f"Wallet not found: {address}", is_error=True)

  try:
    if chain_type == "evm":
      account = wallet.get_account()
      # Sign message using eth_account's sign_message
      from eth_account.messages import encode_defunct

      message_hash = encode_defunct(text=message)
      signed = account.sign_message(message_hash)
      return ToolResult(
        content=json.dumps(
          {
            "address": address,
            "message": message,
            "signature": signed.signature.hex(),
          },
          indent=2,
        )
      )
    elif chain_type == "sol":
      # Solana message signing would go here
      return ToolResult(content="Solana message signing not yet implemented", is_error=True)
    else:
      return ToolResult(content=f"Unsupported chain type: {chain_type}", is_error=True)
  except Exception as exc:
    return ToolResult(content=f"Failed to sign message: {exc}", is_error=True)
