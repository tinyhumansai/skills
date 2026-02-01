#!/usr/bin/env python3
"""
Test initial sync + expanded update handlers against a live Telegram account.

Loads the Telegram skill, waits for the background initial sync to complete,
then queries the database and in-memory store to verify everything populated
correctly. Optionally listens for live updates for a few seconds to verify
the expanded raw event handlers.

Usage:
    python scripts/test-sync.py [--listen N] [--verbose]

    --listen N   After sync, listen for live updates for N seconds (default: 0)
    --verbose    Show detailed chat/message/user breakdowns

Requires a saved session in skills/telegram/data/config.json
(created by test-setup.py).
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path setup — must happen before any skill imports
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SKILL_DIR = ROOT / "skills" / "telegram"
DATA_DIR = SKILL_DIR / "data"
CONFIG_PATH = DATA_DIR / "config.json"

# Pre-import packages that depend on stdlib email before skills/ shadows it
import email.message  # noqa: F401
import importlib.metadata  # noqa: F401

if str(SKILL_DIR.parent) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR.parent))

import logging

logging.basicConfig(
    level=logging.INFO,
    format="\033[2m[%(name)s] %(message)s\033[0m",
    stream=sys.stderr,
)
log = logging.getLogger("test-sync")

# ---------------------------------------------------------------------------
# Console helpers
# ---------------------------------------------------------------------------

BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
RESET = "\033[0m"


def bold(s: str) -> str:
    return f"{BOLD}{s}{RESET}"


def dim(s: str) -> str:
    return f"{DIM}{s}{RESET}"


def green(s: str) -> str:
    return f"{GREEN}{s}{RESET}"


def red(s: str) -> str:
    return f"{RED}{s}{RESET}"


def cyan(s: str) -> str:
    return f"{CYAN}{s}{RESET}"


def magenta(s: str) -> str:
    return f"{MAGENTA}{s}{RESET}"


def yellow(s: str) -> str:
    return f"{YELLOW}{s}{RESET}"


def check(label: str, passed: bool, detail: str = "") -> bool:
    icon = green("PASS") if passed else red("FAIL")
    line = f"  {icon} {label}"
    if detail:
        line += f" — {dim(detail)}"
    print(line)
    return passed


# ---------------------------------------------------------------------------
# DB verification helpers
# ---------------------------------------------------------------------------


async def query_db_stats(db: Any) -> dict[str, Any]:
    """Query counts and samples from each table."""
    stats: dict[str, Any] = {}

    # Chat count
    cursor = await db.execute("SELECT count(*) FROM chats")
    row = await cursor.fetchone()
    stats["chat_count"] = row[0]

    # Message count
    cursor = await db.execute("SELECT count(*) FROM messages")
    row = await cursor.fetchone()
    stats["message_count"] = row[0]

    # User count
    cursor = await db.execute("SELECT count(*) FROM users")
    row = await cursor.fetchone()
    stats["user_count"] = row[0]

    # Event count
    cursor = await db.execute("SELECT count(*) FROM events")
    row = await cursor.fetchone()
    stats["event_count"] = row[0]

    # Event types breakdown
    cursor = await db.execute(
        "SELECT event_type, count(*) FROM events GROUP BY event_type ORDER BY count(*) DESC"
    )
    rows = await cursor.fetchall()
    stats["event_types"] = {row[0]: row[1] for row in rows}

    # Update state
    cursor = await db.execute("SELECT pts, qts, date, seq FROM update_state WHERE key = 'global'")
    row = await cursor.fetchone()
    stats["update_state"] = (
        {"pts": row[0], "qts": row[1], "date": row[2], "seq": row[3]} if row else None
    )

    # Channel pts count
    cursor = await db.execute("SELECT count(*) FROM channel_pts")
    row = await cursor.fetchone()
    stats["channel_pts_count"] = row[0]

    # Pinned chats
    cursor = await db.execute("SELECT count(*) FROM chats WHERE is_pinned = 1")
    row = await cursor.fetchone()
    stats["pinned_chat_count"] = row[0]

    # Chats with messages
    cursor = await db.execute("SELECT count(DISTINCT chat_id) FROM messages")
    row = await cursor.fetchone()
    stats["chats_with_messages"] = row[0]

    # Sample chats (top 5)
    cursor = await db.execute(
        "SELECT id, title, type, unread_count, is_pinned FROM chats ORDER BY sort_order ASC LIMIT 5"
    )
    rows = await cursor.fetchall()
    stats["sample_chats"] = [
        {"id": r[0], "title": r[1], "type": r[2], "unread": r[3], "pinned": bool(r[4])}
        for r in rows
    ]

    # Messages per chat (top 5)
    cursor = await db.execute(
        "SELECT chat_id, count(*) as cnt FROM messages GROUP BY chat_id ORDER BY cnt DESC LIMIT 5"
    )
    rows = await cursor.fetchall()
    stats["top_message_chats"] = [{"chat_id": r[0], "count": r[1]} for r in rows]

    return stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main_async() -> int:
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    # Parse --listen N
    listen_seconds = 0
    for i, arg in enumerate(sys.argv):
        if arg == "--listen" and i + 1 < len(sys.argv):
            try:
                listen_seconds = int(sys.argv[i + 1])
            except ValueError:
                pass

    print()
    print(bold("  Initial Sync + Update Handler Test"))
    print()

    # Load config
    if not CONFIG_PATH.exists():
        print(red("  No config found. Run scripts/test-setup.py first."))
        return 1

    config = json.loads(CONFIG_PATH.read_text())
    api_id = config.get("api_id", 0)
    api_hash = config.get("api_hash", "")
    session_string = config.get("session_string", "")

    if not api_id or not api_hash or not session_string:
        print(red("  Incomplete config. Run scripts/test-setup.py first."))
        return 1

    print(dim(f"  API ID: {api_id}"))
    print(dim(f"  Session: found"))
    print()

    # -----------------------------------------------------------------------
    # Phase 1: Load skill (triggers initial sync in background)
    # -----------------------------------------------------------------------
    print(bold("  Phase 1: Loading skill + initial sync"))
    print()

    from telegram.server import on_skill_load, on_skill_unload
    from telegram.state import store

    data_dir = str(DATA_DIR)

    load_start = time.monotonic()
    await on_skill_load(
        params={
            "apiId": str(api_id),
            "apiHash": api_hash,
            "sessionString": session_string,
            "dataDir": data_dir,
        },
    )

    state = store.get_state()
    if state.auth_status != "authenticated":
        print(red(f"  Authentication failed (status: {state.auth_status})"))
        await on_skill_unload()
        return 1

    user = state.current_user
    name = (user.first_name or user.username or str(user.id)) if user else "?"
    print(green(f"  Connected as {name}"))
    print()

    # -----------------------------------------------------------------------
    # Phase 2: Wait for initial sync to complete
    # -----------------------------------------------------------------------
    print(bold("  Phase 2: Waiting for initial sync"))
    print()

    max_wait = 120  # seconds
    poll_interval = 1
    waited = 0
    last_chat_count = 0

    while waited < max_wait:
        state = store.get_state()
        chat_count = len(state.chats_order)

        if chat_count != last_chat_count:
            print(dim(f"    {chat_count} chats loaded... (syncing={state.is_syncing})"))
            last_chat_count = chat_count

        if state.initial_sync_complete:
            break

        await asyncio.sleep(poll_interval)
        waited += poll_interval

    load_duration = time.monotonic() - load_start
    state = store.get_state()

    if state.initial_sync_complete:
        print(green(f"  Initial sync completed in {load_duration:.1f}s"))
    else:
        print(yellow(f"  Sync still running after {max_wait}s — continuing with partial results"))
    print()

    # -----------------------------------------------------------------------
    # Phase 3: Verify in-memory store
    # -----------------------------------------------------------------------
    print(bold("  Phase 3: In-memory store verification"))
    print(f"  {'─' * 50}")

    errors = 0

    if not check("Chats loaded", len(state.chats_order) > 0, f"{len(state.chats_order)} chats"):
        errors += 1
    if not check("Users cached", len(state.users) > 0, f"{len(state.users)} users"):
        errors += 1
    if not check("Auth status", state.auth_status == "authenticated"):
        errors += 1
    if not check("Connection status", state.connection_status == "connected"):
        errors += 1
    if not check("Current user set", state.current_user is not None):
        errors += 1
    if not check("Sync complete flag", state.initial_sync_complete):
        errors += 1
    if not check("Not syncing", not state.is_syncing):
        errors += 1
    if not check("Is synced", state.is_synced):
        errors += 1

    # Check sync pts
    has_pts = state.sync_pts > 0 or state.sync_seq > 0
    if not check("Update state tracked", has_pts, f"pts={state.sync_pts} seq={state.sync_seq}"):
        errors += 1

    # Check messages were preloaded
    total_messages = sum(len(msgs) for msgs in state.messages.values())
    if not check(
        "Messages preloaded",
        total_messages > 0,
        f"{total_messages} messages across {len(state.messages)} chats",
    ):
        errors += 1

    # Check for pinned chats
    pinned = [c for c in state.chats.values() if c.is_pinned]
    check("Pinned chats detected", len(pinned) > 0, f"{len(pinned)} pinned")

    # Verbose: show top chats
    if verbose:
        print()
        print(f"  {bold('Top 10 chats:')}")
        for i, cid in enumerate(state.chats_order[:10], 1):
            chat = state.chats.get(cid)
            if not chat:
                continue
            pin = " 📌" if chat.is_pinned else ""
            muted = " 🔇" if chat.is_muted else ""
            archived = " 📦" if chat.is_archived else ""
            draft = " ✏️" if chat.draft_message else ""
            unread = f" ({chat.unread_count} unread)" if chat.unread_count else ""
            print(
                f"    {cyan(str(i))}. [{dim(chat.type[:4])}] "
                f"{chat.title or chat.id}{pin}{muted}{archived}{draft}{unread}"
            )

    print()

    # -----------------------------------------------------------------------
    # Phase 4: Verify SQLite database
    # -----------------------------------------------------------------------
    print(bold("  Phase 4: SQLite database verification"))
    print(f"  {'─' * 50}")

    from telegram.db.connection import get_db

    db = await get_db()
    db_stats = await query_db_stats(db)

    if not check("DB chats", db_stats["chat_count"] > 0, f"{db_stats['chat_count']} rows"):
        errors += 1
    if not check("DB users", db_stats["user_count"] > 0, f"{db_stats['user_count']} rows"):
        errors += 1
    if not check("DB messages", db_stats["message_count"] > 0, f"{db_stats['message_count']} rows"):
        errors += 1

    us = db_stats["update_state"]
    if not check(
        "DB update_state", us is not None, f"pts={us['pts']} seq={us['seq']}" if us else "not saved"
    ):
        errors += 1

    if not check(
        "DB channel_pts",
        db_stats["channel_pts_count"] > 0,
        f"{db_stats['channel_pts_count']} channels",
    ):
        errors += 1

    check(
        "DB pinned chats",
        db_stats["pinned_chat_count"] > 0,
        f"{db_stats['pinned_chat_count']} pinned",
    )
    check(
        "DB chats with messages",
        db_stats["chats_with_messages"] > 0,
        f"{db_stats['chats_with_messages']} chats",
    )

    if verbose:
        print()
        print(f"  {bold('Sample chats (DB):')}")
        for sc in db_stats["sample_chats"]:
            pin = " 📌" if sc["pinned"] else ""
            print(
                f"    [{dim(sc['type'][:4])}] {sc['title'] or sc['id']}{pin} (unread: {sc['unread']})"
            )

        print()
        print(f"  {bold('Top message-heavy chats (DB):')}")
        for tc in db_stats["top_message_chats"]:
            chat = state.chats.get(tc["chat_id"])
            title = chat.title if chat else tc["chat_id"]
            print(f"    {title}: {tc['count']} messages")

    print()

    # -----------------------------------------------------------------------
    # Phase 5: Consistency checks
    # -----------------------------------------------------------------------
    print(bold("  Phase 5: Store ↔ DB consistency"))
    print(f"  {'─' * 50}")

    # Store chat count should roughly match DB
    store_chats = len(state.chats_order)
    db_chats = db_stats["chat_count"]
    diff = abs(store_chats - db_chats)
    check(
        "Chat count consistency",
        diff <= max(5, store_chats * 0.05),
        f"store={store_chats}, db={db_chats}, diff={diff}",
    )

    # Store users should be >= DB users (store may have more from message senders)
    store_users = len(state.users)
    db_users = db_stats["user_count"]
    check(
        "User count plausible",
        store_users > 0 and db_users > 0,
        f"store={store_users}, db={db_users}",
    )

    print()

    # -----------------------------------------------------------------------
    # Phase 6 (optional): Listen for live updates
    # -----------------------------------------------------------------------
    if listen_seconds > 0:
        print(bold(f"  Phase 6: Listening for live updates ({listen_seconds}s)"))
        print(f"  {'─' * 50}")
        print(dim("  Waiting for incoming messages, typing, reads, etc."))
        print()

        # Snapshot event count before
        cursor = await db.execute("SELECT count(*) FROM events")
        row = await cursor.fetchone()
        events_before = row[0]

        await asyncio.sleep(listen_seconds)

        # Check new events
        cursor = await db.execute("SELECT count(*) FROM events")
        row = await cursor.fetchone()
        events_after = row[0]
        new_events = events_after - events_before

        # Get breakdown of new event types
        cursor = await db.execute(
            "SELECT event_type, count(*) FROM events WHERE created_at >= ? "
            "GROUP BY event_type ORDER BY count(*) DESC",
            (time.time() - listen_seconds,),
        )
        rows = await cursor.fetchall()
        new_event_types = {row[0]: row[1] for row in rows}

        check("Events captured during listen", new_events > 0, f"{new_events} new events")

        if new_event_types:
            print()
            print(f"  {bold('Events by type:')}")
            for etype, count in new_event_types.items():
                print(f"    {cyan(etype)}: {count}")
        else:
            print(dim("  No events received (try sending a message from another device)"))

        print()

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print(bold("  Summary"))
    print(f"  {'─' * 50}")
    print(f"  Chats:       {green(str(len(state.chats_order)))}")
    print(f"  Users:       {green(str(len(state.users)))}")
    print(f"  Messages:    {green(str(total_messages))} (in-memory)")
    print(f"  DB messages: {green(str(db_stats['message_count']))}")
    print(f"  Sync time:   {green(f'{load_duration:.1f}s')}")
    print(f"  Errors:      {red(str(errors)) if errors else green('0')}")

    if db_stats["event_types"]:
        print()
        print(f"  {bold('All event types in DB:')}")
        for etype, count in db_stats["event_types"].items():
            print(f"    {cyan(etype)}: {count}")

    print()

    # Cleanup
    print(dim("  Disconnecting..."))
    await on_skill_unload()
    print(dim("  Done."))
    print()

    return 1 if errors > 0 else 0


def main() -> None:
    try:
        code = asyncio.run(main_async())
    except KeyboardInterrupt:
        print(f"\n\n  {yellow('Interrupted.')}\n")
        code = 130
    sys.exit(code)


if __name__ == "__main__":
    main()
