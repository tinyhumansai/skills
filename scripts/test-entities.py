#!/usr/bin/env python3
"""
Test entity emission against a live Telegram account.

Loads the Telegram skill with mock entity/relationship callbacks,
connects to the account, and verifies that entities are emitted.
After load, runs one tick to test summary emission.

Usage:
    python scripts/test-entities.py [--tick] [--verbose]

    --tick     Also run on_skill_tick to test summary emission
    --verbose  Show full entity metadata

Requires a saved session in skills/telegram/data/config.json
(created by test-setup.py).
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path setup
#
# IMPORTANT: skills/ contains a directory called "email" which shadows the
# stdlib email module. We must import mcp/pydantic/telethon *before* adding
# skills/ to sys.path.
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SKILL_DIR = ROOT / "skills" / "telegram"
DATA_DIR = SKILL_DIR / "data"
CONFIG_PATH = DATA_DIR / "config.json"

# Pre-import packages that depend on stdlib email before skills/ is on path
import email.message  # noqa: F401 — warm stdlib before skills/ shadows it
import importlib.metadata  # noqa: F401

if str(SKILL_DIR.parent) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR.parent))

import logging

logging.basicConfig(
    level=logging.INFO,
    format="\033[2m[%(name)s] %(message)s\033[0m",
    stream=sys.stderr,
)

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


# ---------------------------------------------------------------------------
# Entity / relationship collectors
# ---------------------------------------------------------------------------


class EntityCollector:
    """Collects entities and relationships emitted by the skill."""

    def __init__(self) -> None:
        self.entities: dict[str, dict[str, Any]] = {}  # keyed by "type:source_id"
        self.relationships: list[dict[str, Any]] = []
        self.entity_count = 0
        self.relationship_count = 0

    async def upsert_entity(
        self,
        *,
        type: str,
        source: str,
        id: str | None = None,
        source_id: str | None = None,
        title: str | None = None,
        summary: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        key = f"{type}:{source_id or id or '?'}"
        self.entities[key] = {
            "type": type,
            "source": source,
            "id": id,
            "source_id": source_id,
            "title": title,
            "summary": summary,
            "metadata": metadata or {},
        }
        self.entity_count += 1

    async def upsert_relationship(
        self,
        *,
        source_id: str,
        target_id: str,
        type: str,
        source: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.relationships.append(
            {
                "source_id": source_id,
                "target_id": target_id,
                "type": type,
                "source": source,
                "metadata": metadata or {},
            }
        )
        self.relationship_count += 1

    def print_summary(self, verbose: bool = False) -> None:
        """Print a summary of collected entities and relationships."""
        # Group entities by type
        by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for key, entity in self.entities.items():
            by_type[entity["type"]].append(entity)

        print()
        print(bold("  Entity Summary"))
        print(f"  {'─' * 50}")
        print(f"  Total entities:      {green(str(len(self.entities)))}")
        print(f"  Total upsert calls:  {dim(str(self.entity_count))}")
        print(f"  Total relationships: {green(str(len(self.relationships)))}")
        print(f"  Total rel calls:     {dim(str(self.relationship_count))}")
        print()

        for etype, entities in sorted(by_type.items()):
            print(f"  {cyan(etype)} — {len(entities)} entities")
            if verbose:
                for e in entities[:10]:
                    title = e.get("title", "?")
                    sid = e.get("source_id", "?")
                    meta_keys = list(e.get("metadata", {}).keys())
                    print(f"    {dim(sid)} {bold(title)}")
                    if meta_keys:
                        print(f"      metadata: {dim(', '.join(meta_keys))}")
                if len(entities) > 10:
                    print(f"    {dim(f'... and {len(entities) - 10} more')}")
            print()

        # Group relationships by type
        rel_by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for rel in self.relationships:
            rel_by_type[rel["type"]].append(rel)

        if self.relationships:
            print(f"  {bold('Relationships')}")
            print()
            for rtype, rels in sorted(rel_by_type.items()):
                print(f"  {magenta(rtype)} — {len(rels)} edges")
                if verbose:
                    for r in rels[:5]:
                        print(f"    {dim(r['source_id'])} → {dim(r['target_id'])}")
                    if len(rels) > 5:
                        print(f"    {dim(f'... and {len(rels) - 5} more')}")
            print()

    def export_graph(self) -> dict[str, Any]:
        """Export the full graph as a JSON-serializable dict."""
        return {
            "entities": list(self.entities.values()),
            "relationships": self.relationships,
            "stats": {
                "entity_count": len(self.entities),
                "relationship_count": len(self.relationships),
                "entity_upsert_calls": self.entity_count,
                "relationship_upsert_calls": self.relationship_count,
                "by_type": {
                    etype: sum(1 for e in self.entities.values() if e["type"] == etype)
                    for etype in sorted({e["type"] for e in self.entities.values()})
                },
            },
        }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main_async() -> int:
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    run_tick = "--tick" in sys.argv

    print()
    print(bold("  Entity Emission Test"))
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
    print(dim(f"  Session: {'found' if session_string else 'none'}"))
    print()

    # Create collector
    collector = EntityCollector()

    # Load skill
    print(dim("  Loading skill with entity callbacks..."))

    from telegram.server import on_skill_load, on_skill_unload, on_skill_tick
    from telegram.state import store

    data_dir = str(DATA_DIR)

    await on_skill_load(
        params={
            "apiId": str(api_id),
            "apiHash": api_hash,
            "sessionString": session_string,
            "dataDir": data_dir,
        },
        upsert_entity_fn=collector.upsert_entity,
        upsert_relationship_fn=collector.upsert_relationship,
    )

    state = store.get_state()

    if state.auth_status != "authenticated":
        print(red(f"  Authentication failed (status: {state.auth_status})"))
        print(yellow("  Try running: python scripts/test-setup.py skills/telegram"))
        await on_skill_unload()
        return 1

    user = state.current_user
    if user:
        name = user.first_name or user.username or str(user.id)
        print(green(f"  Connected as {name}"))
    else:
        print(green("  Connected"))

    print(dim(f"  Chats in store: {len(state.chats_order)}"))
    print(dim(f"  Users in store: {len(state.users)}"))
    print()

    # Show load results
    print(bold("  === After on_skill_load ==="))
    collector.print_summary(verbose=verbose)

    # Fetch dialogs + contacts to populate the store, then re-emit
    print(bold("  === Fetching dialogs + contacts ==="))
    print(dim("  Calling get_chats(100) to populate chat store..."))

    from telegram.api.chat_api import get_chats as api_get_chats
    from telegram.api.contact_api import list_contacts as api_list_contacts
    from telegram.entities import emit_initial_entities

    chat_result = await api_get_chats(100)
    print(dim(f"  Fetched {len(chat_result.data)} chats (from_cache={chat_result.from_cache})"))

    print(dim("  Calling list_contacts(200) to populate user store..."))
    contact_result = await api_list_contacts(200)
    contacts_fetched = contact_result.data
    print(dim(f"  Fetched {len(contacts_fetched)} contacts"))

    # Add fetched contacts to the store
    if contacts_fetched:
        user_dict = {u.id: u for u in contacts_fetched}
        store.add_users(user_dict)

    state = store.get_state()
    print(dim(f"  Chats in store now: {len(state.chats_order)}"))
    print(dim(f"  Users in store now: {len(state.users)}"))
    print()

    # Re-emit entities now that the store is populated
    print(dim("  Re-emitting entities with populated store..."))
    await emit_initial_entities(collector.upsert_entity, collector.upsert_relationship)

    print(bold("  === After dialog + contact fetch ==="))
    collector.print_summary(verbose=verbose)

    # Optionally run a tick
    if run_tick:
        pre_entities = len(collector.entities)
        pre_rels = len(collector.relationships)

        print(bold("  === Running on_skill_tick ==="))
        print(dim("  Generating summaries + emitting entities..."))
        print()

        await on_skill_tick()

        new_entities = len(collector.entities) - pre_entities
        new_rels = len(collector.relationships) - pre_rels
        print(dim(f"  New entities from tick: {new_entities}"))
        print(dim(f"  New relationships from tick: {new_rels}"))
        print()

        print(bold("  === After on_skill_tick ==="))
        collector.print_summary(verbose=verbose)

    # Export graph to file
    graph_path = DATA_DIR / "entity_graph.json"
    graph = collector.export_graph()
    graph_path.write_text(json.dumps(graph, indent=2, ensure_ascii=False))
    print(dim(f"  Graph exported to {graph_path}"))
    print()

    # Validation checks
    print(bold("  Validation"))
    print(f"  {'─' * 50}")
    errors = 0

    if len(collector.entities) == 0:
        print(f"  {red('FAIL')} No entities emitted")
        errors += 1
    else:
        print(f"  {green('PASS')} Entities emitted: {len(collector.entities)}")

    # Check entity types match schema
    expected_types = {
        "telegram.contact",
        "telegram.group",
        "telegram.channel",
        "telegram.dm",
        "telegram.summary",
        "telegram.thread",
    }
    actual_types = {e["type"] for e in collector.entities.values()}
    base_types = actual_types - {"telegram.summary", "telegram.thread"}
    if base_types:
        print(f"  {green('PASS')} Entity types: {', '.join(sorted(actual_types))}")
    else:
        print(f"  {yellow('WARN')} Only types: {', '.join(sorted(actual_types))}")

    # Check contacts emitted
    contacts = [e for e in collector.entities.values() if e["type"] == "telegram.contact"]
    if contacts:
        print(f"  {green('PASS')} Contacts emitted: {len(contacts)}")
        # Check current user has is_self
        self_contacts = [c for c in contacts if c.get("metadata", {}).get("is_self")]
        if self_contacts:
            print(f"  {green('PASS')} Current user marked is_self=True")
        else:
            print(f"  {yellow('WARN')} No contact with is_self=True")
    else:
        print(f"  {red('FAIL')} No contacts emitted")
        errors += 1

    # Check chats
    chat_entities = [
        e
        for e in collector.entities.values()
        if e["type"] in ("telegram.group", "telegram.channel", "telegram.dm")
    ]
    if chat_entities:
        print(f"  {green('PASS')} Chat entities emitted: {len(chat_entities)}")
    else:
        print(f"  {red('FAIL')} No chat entities emitted")
        errors += 1

    # Check relationships
    if collector.relationships:
        print(f"  {green('PASS')} Relationships emitted: {len(collector.relationships)}")
        dm_with = [r for r in collector.relationships if r["type"] == "dm_with"]
        if dm_with:
            print(f"  {green('PASS')} dm_with relationships: {len(dm_with)}")
    else:
        print(f"  {yellow('WARN')} No relationships emitted")

    # Summary check (only if tick ran)
    if run_tick:
        summaries = [e for e in collector.entities.values() if e["type"] == "telegram.summary"]
        if summaries:
            print(f"  {green('PASS')} Summary entities emitted: {len(summaries)}")
            summary_rels = [
                r for r in collector.relationships if r["type"] in ("summarizes", "summarizes_dm")
            ]
            if summary_rels:
                print(f"  {green('PASS')} Summary relationships: {len(summary_rels)}")
        else:
            print(f"  {yellow('WARN')} No summary entities (may be first run with no messages)")

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
