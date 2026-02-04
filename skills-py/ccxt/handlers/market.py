"""
Market data handlers.
"""

from __future__ import annotations

from typing import Any

from ..client.ccxt_client import get_ccxt_manager
from ..helpers import ErrorCategory, ToolResult, log_and_format_error
from ..validation import opt_number, opt_string_list, req_string


async def fetch_ticker(args: dict[str, Any]) -> ToolResult:
  """Fetch ticker data for a trading pair."""
  try:
    exchange_id = req_string(args, "exchange_id")
    symbol = req_string(args, "symbol")
    manager = get_ccxt_manager()
    if not manager:
      return ToolResult(content="CCXT manager not initialized.", is_error=True)

    exchange = manager.get_exchange(exchange_id)
    if not exchange:
      return ToolResult(content=f"Exchange '{exchange_id}' not found.", is_error=True)

    ticker = await exchange.fetch_ticker(symbol)
    lines = [
      f"Ticker for {symbol} on {exchange_id}:",
      f"  Last: {ticker.get('last', 'N/A')}",
      f"  Bid: {ticker.get('bid', 'N/A')}",
      f"  Ask: {ticker.get('ask', 'N/A')}",
      f"  High: {ticker.get('high', 'N/A')}",
      f"  Low: {ticker.get('low', 'N/A')}",
      f"  Volume: {ticker.get('quoteVolume', ticker.get('volume', 'N/A'))}",
      f"  Change: {ticker.get('percentage', 'N/A')}%",
    ]
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("fetch_ticker", e, ErrorCategory.MARKET)


async def fetch_tickers(args: dict[str, Any]) -> ToolResult:
  """Fetch ticker data for multiple trading pairs."""
  try:
    exchange_id = req_string(args, "exchange_id")
    symbols = opt_string_list(args, "symbols")
    manager = get_ccxt_manager()
    if not manager:
      return ToolResult(content="CCXT manager not initialized.", is_error=True)

    exchange = manager.get_exchange(exchange_id)
    if not exchange:
      return ToolResult(content=f"Exchange '{exchange_id}' not found.", is_error=True)

    if symbols:
      tickers = await exchange.fetch_tickers(symbols)
    else:
      tickers = await exchange.fetch_tickers()

    lines = [f"Tickers for {exchange_id}:"]
    for symbol, ticker in list(tickers.items())[:20]:  # Limit to 20 for readability
      last = ticker.get("last", "N/A")
      change = ticker.get("percentage", "N/A")
      lines.append(f"  {symbol}: {last} ({change}%)")

    if len(tickers) > 20:
      lines.append(f"\n... and {len(tickers) - 20} more")

    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("fetch_tickers", e, ErrorCategory.MARKET)


async def fetch_orderbook(args: dict[str, Any]) -> ToolResult:
  """Fetch order book for a trading pair."""
  try:
    exchange_id = req_string(args, "exchange_id")
    symbol = req_string(args, "symbol")
    limit = opt_number(args, "limit", 20)
    manager = get_ccxt_manager()
    if not manager:
      return ToolResult(content="CCXT manager not initialized.", is_error=True)

    exchange = manager.get_exchange(exchange_id)
    if not exchange:
      return ToolResult(content=f"Exchange '{exchange_id}' not found.", is_error=True)

    orderbook = await exchange.fetch_order_book(symbol, limit)
    bids = orderbook.get("bids", [])
    asks = orderbook.get("asks", [])

    lines = [f"Orderbook for {symbol} on {exchange_id}:"]
    lines.append("\nBids (buy orders):")
    for bid in bids[:10]:
      lines.append(f"  {bid[0]} @ {bid[1]}")

    lines.append("\nAsks (sell orders):")
    for ask in asks[:10]:
      lines.append(f"  {ask[0]} @ {ask[1]}")

    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("fetch_orderbook", e, ErrorCategory.MARKET)


async def fetch_trades(args: dict[str, Any]) -> ToolResult:
  """Fetch recent trades for a trading pair."""
  try:
    exchange_id = req_string(args, "exchange_id")
    symbol = req_string(args, "symbol")
    limit = opt_number(args, "limit", 50)
    manager = get_ccxt_manager()
    if not manager:
      return ToolResult(content="CCXT manager not initialized.", is_error=True)

    exchange = manager.get_exchange(exchange_id)
    if not exchange:
      return ToolResult(content=f"Exchange '{exchange_id}' not found.", is_error=True)

    trades = await exchange.fetch_trades(symbol, limit=limit)
    lines = [f"Recent trades for {symbol} on {exchange_id}:"]
    for trade in trades[:20]:  # Limit display
      side = trade.get("side", "unknown")
      price = trade.get("price", "N/A")
      amount = trade.get("amount", "N/A")
      lines.append(f"  {side.upper()}: {amount} @ {price}")

    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("fetch_trades", e, ErrorCategory.MARKET)


async def fetch_ohlcv(args: dict[str, Any]) -> ToolResult:
  """Fetch OHLCV (candlestick) data."""
  try:
    exchange_id = req_string(args, "exchange_id")
    symbol = req_string(args, "symbol")
    timeframe = req_string(args, "timeframe")
    limit = opt_number(args, "limit", 100)
    manager = get_ccxt_manager()
    if not manager:
      return ToolResult(content="CCXT manager not initialized.", is_error=True)

    exchange = manager.get_exchange(exchange_id)
    if not exchange:
      return ToolResult(content=f"Exchange '{exchange_id}' not found.", is_error=True)

    ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    lines = [f"OHLCV for {symbol} ({timeframe}) on {exchange_id}:"]
    lines.append("  [Timestamp, Open, High, Low, Close, Volume]")
    for candle in ohlcv[-10:]:  # Show last 10 candles
      lines.append(f"  {candle}")

    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("fetch_ohlcv", e, ErrorCategory.MARKET)


async def fetch_markets(args: dict[str, Any]) -> ToolResult:
  """Fetch all available markets for an exchange."""
  try:
    exchange_id = req_string(args, "exchange_id")
    manager = get_ccxt_manager()
    if not manager:
      return ToolResult(content="CCXT manager not initialized.", is_error=True)

    exchange = manager.get_exchange(exchange_id)
    if not exchange:
      return ToolResult(content=f"Exchange '{exchange_id}' not found.", is_error=True)

    await exchange.load_markets()
    markets = list(exchange.markets.keys())
    lines = [f"Available markets on {exchange_id} ({len(markets)}):"]
    for market in markets[:50]:  # Show first 50
      lines.append(f"  {market}")

    if len(markets) > 50:
      lines.append(f"\n... and {len(markets) - 50} more")

    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("fetch_markets", e, ErrorCategory.MARKET)
