"""
CCXT skill entry point — starts the MCP server.
"""

from __future__ import annotations

import asyncio
import logging
import sys

from mcp.server.stdio import stdio_server

from .server import create_mcp_server

logging.basicConfig(
  level=logging.INFO,
  format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
  stream=sys.stderr,
)

log = logging.getLogger("skill.ccxt")


async def main() -> None:
  """Start the MCP server."""
  server = create_mcp_server()
  async with stdio_server() as (read_stream, write_stream):
    await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
  asyncio.run(main())
