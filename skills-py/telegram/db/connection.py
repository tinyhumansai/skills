"""
Shared aiosqlite connection management.
"""

from __future__ import annotations

import logging
import os

import aiosqlite

from .schema import PRAGMA_SQL, SCHEMA_SQL

log = logging.getLogger("skill.telegram.db")

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
  """Return the shared database connection, creating it if needed."""
  global _db
  if _db is None:
    raise RuntimeError("Database not initialized. Call init_db() first.")
  return _db


async def init_db(data_dir: str) -> aiosqlite.Connection:
  """Initialize the SQLite database."""
  global _db
  os.makedirs(data_dir, exist_ok=True)
  db_path = os.path.join(data_dir, "telegram.db")
  log.info("Opening database at %s", db_path)

  _db = await aiosqlite.connect(db_path)
  _db.row_factory = aiosqlite.Row

  # Set pragmas
  for line in PRAGMA_SQL.strip().splitlines():
    line = line.strip()
    if line and not line.startswith("--"):
      await _db.execute(line)

  # Create schema
  await _db.executescript(SCHEMA_SQL)
  await _db.commit()

  log.info("Database initialized")
  return _db


async def close_db() -> None:
  """Close the database connection."""
  global _db
  if _db is not None:
    await _db.close()
    _db = None
    log.info("Database closed")
