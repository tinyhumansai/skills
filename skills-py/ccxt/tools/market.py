"""
Market data tools.
"""

from __future__ import annotations

from mcp.types import Tool

market_tools: list[Tool] = [
  Tool(
    name="fetch_ticker",
    description="Get ticker data for a trading pair",
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
      },
      "required": ["exchange_id", "symbol"],
    },
  ),
  Tool(
    name="fetch_tickers",
    description="Get ticker data for multiple trading pairs",
    inputSchema={
      "type": "object",
      "properties": {
        "exchange_id": {
          "type": "string",
          "description": "The exchange connection ID",
        },
        "symbols": {
          "type": "array",
          "items": {"type": "string"},
          "description": "List of trading pair symbols (e.g., ['BTC/USDT', 'ETH/USDT'])",
        },
      },
      "required": ["exchange_id"],
    },
  ),
  Tool(
    name="fetch_orderbook",
    description="Get order book for a trading pair",
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
        "limit": {
          "type": "number",
          "description": "Number of orders to return (default: 20)",
        },
      },
      "required": ["exchange_id", "symbol"],
    },
  ),
  Tool(
    name="fetch_trades",
    description="Get recent trades for a trading pair",
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
        "limit": {
          "type": "number",
          "description": "Number of trades to return (default: 50)",
        },
      },
      "required": ["exchange_id", "symbol"],
    },
  ),
  Tool(
    name="fetch_ohlcv",
    description="Get OHLCV (candlestick) data for a trading pair",
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
        "timeframe": {
          "type": "string",
          "description": "Timeframe (e.g., '1m', '5m', '1h', '1d')",
        },
        "limit": {
          "type": "number",
          "description": "Number of candles to return (default: 100)",
        },
      },
      "required": ["exchange_id", "symbol", "timeframe"],
    },
  ),
  Tool(
    name="fetch_markets",
    description="Get all available markets for an exchange",
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
]
