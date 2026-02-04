"""
Tool definitions for the wallet skill.

These tools are exposed to the AI agent for wallet operations.
"""

from __future__ import annotations

from mcp.types import Tool

ALL_TOOLS: list[Tool] = [
  Tool(
    name="list_wallets",
    description="List all configured wallet accounts (EVM and Solana)",
    inputSchema={
      "type": "object",
      "properties": {},
      "required": [],
    },
  ),
  Tool(
    name="list_networks",
    description="List all configured blockchain networks with connection status",
    inputSchema={
      "type": "object",
      "properties": {},
      "required": [],
    },
  ),
  Tool(
    name="get_balance",
    description="Get the balance of a wallet address on a specific network",
    inputSchema={
      "type": "object",
      "properties": {
        "address": {
          "type": "string",
          "description": "Wallet address to check balance for",
        },
        "chain_id": {
          "type": "string",
          "description": "Chain ID of the network (e.g., '1' for Ethereum, 'mainnet-beta' for Solana)",
        },
        "chain_type": {
          "type": "string",
          "enum": ["evm", "sol"],
          "description": "Chain type: 'evm' for Ethereum-compatible chains, 'sol' for Solana",
          "default": "evm",
        },
      },
      "required": ["address", "chain_id"],
    },
  ),
  Tool(
    name="send_transaction",
    description="Send a transaction from one address to another on a blockchain network",
    inputSchema={
      "type": "object",
      "properties": {
        "from_address": {
          "type": "string",
          "description": "Source wallet address",
        },
        "to_address": {
          "type": "string",
          "description": "Destination wallet address",
        },
        "amount": {
          "type": "string",
          "description": "Amount to send (as decimal string, e.g., '0.1' for 0.1 ETH)",
        },
        "chain_id": {
          "type": "string",
          "description": "Chain ID of the network",
        },
        "chain_type": {
          "type": "string",
          "enum": ["evm", "sol"],
          "description": "Chain type: 'evm' or 'sol'",
          "default": "evm",
        },
        "gas_limit": {
          "type": "integer",
          "description": "Gas limit for EVM transactions (optional)",
        },
      },
      "required": ["from_address", "to_address", "amount", "chain_id"],
    },
  ),
  Tool(
    name="sign_message",
    description="Sign a message with a wallet's private key",
    inputSchema={
      "type": "object",
      "properties": {
        "address": {
          "type": "string",
          "description": "Wallet address to sign with",
        },
        "message": {
          "type": "string",
          "description": "Message to sign",
        },
        "chain_type": {
          "type": "string",
          "enum": ["evm", "sol"],
          "description": "Chain type: 'evm' or 'sol'",
          "default": "evm",
        },
      },
      "required": ["address", "message"],
    },
  ),
]
