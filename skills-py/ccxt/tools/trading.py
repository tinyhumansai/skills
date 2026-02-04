"""
Trading tools (orders, balance, positions).
"""

from __future__ import annotations

from mcp.types import Tool

trading_tools: list[Tool] = [
  Tool(
    name="fetch_balance",
    description="Get account balance for an exchange",
    inputSchema={
      "type": "object",
      "properties": {
        "exchange_id": {
          "type": "string",
          "description": "The exchange connection ID",
        },
      },
      "required": ["exchange_id"],
    },
  ),
  Tool(
    name="create_order",
    description="Create a new order (market or limit)",
    inputSchema={
      "type": "object",
      "properties": {
        "exchange_id": {
          "type": "string",
          "description": "The exchange connection ID",
        },
        "symbol": {
          "type": "string",
          "description": "Trading pair symbol (e.g., 'BTC/USDT')",
        },
        "side": {
          "type": "string",
          "description": "Order side: 'buy' or 'sell'",
          "enum": ["buy", "sell"],
        },
        "type": {
          "type": "string",
          "description": "Order type: 'market' or 'limit'",
          "enum": ["market", "limit"],
        },
        "amount": {
          "type": "number",
          "description": "Order amount in base currency",
        },
        "price": {
          "type": "number",
          "description": "Limit price (required for limit orders)",
        },
        "settings": {
          "type": "array",
          "description": "Optional array of setting objects to pass to the order. Each object can have key-value pairs for order parameters.",
          "items": {
            "type": "object",
            "description": "Setting object with order parameters",
          },
        },
      },
      "required": ["exchange_id", "symbol", "side", "type", "amount"],
    },
  ),
  Tool(
    name="cancel_order",
    description="Cancel an open order",
    inputSchema={
      "type": "object",
      "properties": {
        "exchange_id": {
          "type": "string",
          "description": "The exchange connection ID",
        },
        "order_id": {
          "type": "string",
          "description": "The order ID to cancel",
        },
        "symbol": {
          "type": "string",
          "description": "Trading pair symbol (e.g., 'BTC/USDT')",
        },
      },
      "required": ["exchange_id", "order_id", "symbol"],
    },
  ),
  Tool(
    name="fetch_order",
    description="Get order details by ID",
    inputSchema={
      "type": "object",
      "properties": {
        "exchange_id": {
          "type": "string",
          "description": "The exchange connection ID",
        },
        "order_id": {
          "type": "string",
          "description": "The order ID",
        },
        "symbol": {
          "type": "string",
          "description": "Trading pair symbol (e.g., 'BTC/USDT')",
        },
      },
      "required": ["exchange_id", "order_id", "symbol"],
    },
  ),
  Tool(
    name="fetch_orders",
    description="Get all open orders (optionally filtered by symbol)",
    inputSchema={
      "type": "object",
      "properties": {
        "exchange_id": {
          "type": "string",
          "description": "The exchange connection ID",
        },
        "symbol": {
          "type": "string",
          "description": "Trading pair symbol to filter by (optional)",
        },
      },
      "required": ["exchange_id"],
    },
  ),
  Tool(
    name="fetch_open_orders",
    description="Get all open orders (optionally filtered by symbol)",
    inputSchema={
      "type": "object",
      "properties": {
        "exchange_id": {
          "type": "string",
          "description": "The exchange connection ID",
        },
        "symbol": {
          "type": "string",
          "description": "Trading pair symbol to filter by (optional)",
        },
      },
      "required": ["exchange_id"],
    },
  ),
  Tool(
    name="fetch_closed_orders",
    description="Get closed orders (optionally filtered by symbol)",
    inputSchema={
      "type": "object",
      "properties": {
        "exchange_id": {
          "type": "string",
          "description": "The exchange connection ID",
        },
        "symbol": {
          "type": "string",
          "description": "Trading pair symbol to filter by (optional)",
        },
        "limit": {
          "type": "number",
          "description": "Maximum number of orders to return (default: 50)",
        },
      },
      "required": ["exchange_id"],
    },
  ),
  Tool(
    name="fetch_my_trades",
    description="Get your trade history",
    inputSchema={
      "type": "object",
      "properties": {
        "exchange_id": {
          "type": "string",
          "description": "The exchange connection ID",
        },
        "symbol": {
          "type": "string",
          "description": "Trading pair symbol to filter by (optional)",
        },
        "limit": {
          "type": "number",
          "description": "Maximum number of trades to return (default: 50)",
        },
      },
      "required": ["exchange_id"],
    },
  ),
]
