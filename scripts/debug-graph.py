#!/usr/bin/env python3
"""
Debug & inspect the entity graph emitted by the Telegram skill.

Reads the graph from skills/telegram/data/entity_graph.json (written by
test-entities.py) and provides an interactive explorer.

Usage:
    python scripts/debug-graph.py                # Interactive mode
    python scripts/debug-graph.py --stats        # Print stats and exit
    python scripts/debug-graph.py --dump         # Dump all entities
    python scripts/debug-graph.py --find <query> # Search entities by title/id
    python scripts/debug-graph.py --node <id>    # Inspect a single node + edges
    python scripts/debug-graph.py --type <type>  # List entities of a given type
    python scripts/debug-graph.py --dot          # Export DOT (Graphviz) format
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
GRAPH_PATH = ROOT / "skills" / "telegram" / "data" / "entity_graph.json"

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
# Graph loader
# ---------------------------------------------------------------------------


class EntityGraph:
  """In-memory entity graph for inspection."""

  def __init__(self, data: dict[str, Any]) -> None:
    self.entities: list[dict[str, Any]] = data.get("entities", [])
    self.relationships: list[dict[str, Any]] = data.get("relationships", [])
    self.stats: dict[str, Any] = data.get("stats", {})

    # Build indices
    self._by_source_id: dict[str, dict[str, Any]] = {}
    self._by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in self.entities:
      sid = e.get("source_id") or e.get("id") or "?"
      key = f"{e['source']}:{sid}" if e.get("source") else sid
      self._by_source_id[key] = e
      self._by_source_id[sid] = e  # also index by plain source_id
      self._by_type[e["type"]].append(e)

    # Index relationships by source and target
    self._rels_from: dict[str, list[dict[str, Any]]] = defaultdict(list)
    self._rels_to: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in self.relationships:
      self._rels_from[r["source_id"]].append(r)
      self._rels_to[r["target_id"]].append(r)

  def find(self, query: str) -> list[dict[str, Any]]:
    """Search entities by title, source_id, or metadata."""
    q = query.lower()
    results = []
    for e in self.entities:
      title = (e.get("title") or "").lower()
      sid = (e.get("source_id") or "").lower()
      meta_str = json.dumps(e.get("metadata", {})).lower()
      if q in title or q in sid or q in meta_str:
        results.append(e)
    return results

  def get_node(self, node_id: str) -> dict[str, Any] | None:
    """Get entity by source_id (with or without source: prefix)."""
    return self._by_source_id.get(node_id)

  def get_edges(self, node_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Get outgoing and incoming relationships for a node."""
    # Try both raw id and source-prefixed
    outgoing = self._rels_from.get(node_id, [])
    incoming = self._rels_to.get(node_id, [])
    # Also try with telegram: prefix
    if not outgoing and not incoming:
      prefixed = f"telegram:{node_id}"
      outgoing = self._rels_from.get(prefixed, [])
      incoming = self._rels_to.get(prefixed, [])
    return outgoing, incoming

  def entity_types(self) -> dict[str, int]:
    return {t: len(es) for t, es in sorted(self._by_type.items())}

  def relationship_types(self) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for r in self.relationships:
      counts[r["type"]] += 1
    return dict(sorted(counts.items()))


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------


def print_entity(e: dict[str, Any], indent: int = 4) -> None:
  """Print a single entity."""
  pad = " " * indent
  title = e.get("title") or "?"
  etype = e.get("type", "?")
  sid = e.get("source_id") or e.get("id") or "?"
  meta = e.get("metadata", {})

  print(f"{pad}{bold(title)}")
  print(f"{pad}  type:      {cyan(etype)}")
  print(f"{pad}  source_id: {dim(sid)}")

  # Show key metadata (skip 'content' which can be huge)
  display_meta = {k: v for k, v in meta.items() if k != "content"}
  if display_meta:
    for k, v in display_meta.items():
      val_str = str(v)
      if len(val_str) > 80:
        val_str = val_str[:77] + "..."
      print(f"{pad}  {dim(k)}: {val_str}")


def print_relationship(r: dict[str, Any], indent: int = 4) -> None:
  """Print a single relationship."""
  pad = " " * indent
  print(f"{pad}{magenta(r['type'])}: {dim(r['source_id'])} → {dim(r['target_id'])}")


def print_stats(graph: EntityGraph) -> None:
  """Print overall graph statistics."""
  print()
  print(bold("  Graph Statistics"))
  print(f"  {'─' * 50}")
  print(f"  Total entities:      {green(str(len(graph.entities)))}")
  print(f"  Total relationships: {green(str(len(graph.relationships)))}")
  print()

  print(f"  {bold('Entity types:')}")
  for etype, count in graph.entity_types().items():
    bar = "█" * min(count, 40)
    print(f"    {cyan(f'{etype:<24}')} {count:>4}  {dim(bar)}")
  print()

  rel_types = graph.relationship_types()
  if rel_types:
    print(f"  {bold('Relationship types:')}")
    for rtype, count in rel_types.items():
      bar = "█" * min(count, 40)
      print(f"    {magenta(f'{rtype:<24}')} {count:>4}  {dim(bar)}")
    print()

  # Extra stats from export
  if graph.stats:
    calls = graph.stats.get("entity_upsert_calls", 0)
    rel_calls = graph.stats.get("relationship_upsert_calls", 0)
    if calls:
      print(f"  {dim(f'Entity upsert calls:      {calls}')}")
    if rel_calls:
      print(f"  {dim(f'Relationship upsert calls: {rel_calls}')}")
    print()


def print_node_detail(graph: EntityGraph, node_id: str) -> None:
  """Print detailed view of a node and its edges."""
  entity = graph.get_node(node_id)
  if not entity:
    print(f"  {red('Not found:')} {node_id}")
    return

  print()
  print(f"  {bold('Node Detail')}")
  print(f"  {'─' * 50}")
  print_entity(entity, indent=2)

  outgoing, incoming = graph.get_edges(node_id)
  # Also try with source prefix
  sid = entity.get("source_id") or entity.get("id") or ""
  if not outgoing and not incoming:
    prefixed = f"telegram:{sid}"
    outgoing, incoming = graph.get_edges(prefixed)

  if outgoing:
    print()
    print(f"  {bold('Outgoing edges')} ({len(outgoing)}):")
    for r in outgoing:
      target = graph.get_node(r["target_id"])
      target_title = target["title"] if target else r["target_id"]
      print(f"    {magenta(r['type'])} → {bold(target_title)}")

  if incoming:
    print()
    print(f"  {bold('Incoming edges')} ({len(incoming)}):")
    for r in incoming:
      source = graph.get_node(r["source_id"])
      source_title = source["title"] if source else r["source_id"]
      print(f"    {bold(source_title)} → {magenta(r['type'])}")

  if not outgoing and not incoming:
    print()
    print(f"  {dim('No edges connected to this node')}")

  print()


def export_dot(graph: EntityGraph) -> str:
  """Export graph in DOT (Graphviz) format."""
  lines = ["digraph EntityGraph {"]
  lines.append("  rankdir=LR;")
  lines.append("  node [shape=box, style=filled];")
  lines.append("")

  # Color mapping
  colors = {
    "telegram.contact": "#E8F5E9",
    "telegram.group": "#E3F2FD",
    "telegram.channel": "#FFF3E0",
    "telegram.dm": "#F3E5F5",
    "telegram.summary": "#FFF9C4",
    "telegram.thread": "#E0F7FA",
  }

  # Emit nodes
  for e in graph.entities:
    sid = e.get("source_id") or e.get("id") or "?"
    node_id = f"telegram:{sid}".replace('"', '\\"')
    title = (e.get("title") or sid)[:30].replace('"', '\\"')
    etype = e.get("type", "")
    color = colors.get(etype, "#FFFFFF")
    short_type = etype.split(".")[-1] if "." in etype else etype
    label = f"{title}\\n({short_type})"
    lines.append(f'  "{node_id}" [label="{label}", fillcolor="{color}"];')

  lines.append("")

  # Emit edges
  for r in graph.relationships:
    src = r["source_id"].replace('"', '\\"')
    tgt = r["target_id"].replace('"', '\\"')
    rtype = r["type"]
    lines.append(f'  "{src}" -> "{tgt}" [label="{rtype}"];')

  lines.append("}")
  return "\n".join(lines)


# ---------------------------------------------------------------------------
# Interactive mode
# ---------------------------------------------------------------------------


def interactive_repl(graph: EntityGraph) -> None:
  """Interactive graph exploration REPL."""
  print()
  print(bold("  Entity Graph Explorer"))
  print()
  print(f"  Commands:")
  print(f"    {cyan('stats')}         — Show graph statistics")
  print(f"    {cyan('types')}         — List entity types")
  print(f"    {cyan('list <type>')}   — List entities of a type (e.g. list telegram.contact)")
  print(f"    {cyan('find <query>')}  — Search entities")
  print(f"    {cyan('node <id>')}     — Inspect a node and its edges")
  print(f"    {cyan('edges')}         — Show all relationships")
  print(f"    {cyan('dot')}           — Export DOT format to stdout")
  print(f"    {cyan('dump')}          — Dump all entities")
  print(f"    {cyan('q')} / {cyan('quit')}      — Exit")
  print()

  while True:
    try:
      raw = input(f"  {CYAN}graph>{RESET} ").strip()
    except (EOFError, KeyboardInterrupt):
      print()
      break

    if not raw:
      continue

    parts = raw.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if cmd in ("q", "quit", "exit"):
      break

    elif cmd == "stats":
      print_stats(graph)

    elif cmd == "types":
      print()
      for etype, count in graph.entity_types().items():
        print(f"    {cyan(etype)}: {count}")
      print()

    elif cmd == "list":
      if not arg:
        print(f"  {yellow('Usage: list <type>')}")
        continue
      entities = graph._by_type.get(arg, [])
      if not entities:
        # Try partial match
        for t in graph._by_type:
          if arg in t:
            entities = graph._by_type[t]
            arg = t
            break
      if not entities:
        print(f"  {yellow('No entities of type')} {arg}")
        continue
      print()
      print(f"  {bold(arg)} ({len(entities)} entities)")
      print()
      for i, e in enumerate(entities, 1):
        title = e.get("title") or "?"
        sid = e.get("source_id") or "?"
        print(f"    {cyan(f'{i:>3}')}. {bold(title)} {dim(f'({sid})')}")
      print()

    elif cmd == "find":
      if not arg:
        print(f"  {yellow('Usage: find <query>')}")
        continue
      results = graph.find(arg)
      if not results:
        print(f"  {yellow('No results for')} {arg}")
        continue
      print()
      print(f"  {bold(f'Results for "{arg}"')} ({len(results)})")
      print()
      for e in results[:20]:
        title = e.get("title") or "?"
        sid = e.get("source_id") or "?"
        etype = e.get("type", "?")
        print(f"    {cyan(etype)} {bold(title)} {dim(f'({sid})')}")
      if len(results) > 20:
        print(f"    {dim(f'... and {len(results) - 20} more')}")
      print()

    elif cmd == "node":
      if not arg:
        print(f"  {yellow('Usage: node <source_id>')}")
        continue
      print_node_detail(graph, arg)

    elif cmd == "edges":
      print()
      rel_types = graph.relationship_types()
      for rtype, count in rel_types.items():
        print(f"  {magenta(rtype)} ({count} edges)")
        for r in graph.relationships:
          if r["type"] == rtype:
            src = r["source_id"]
            tgt = r["target_id"]
            src_entity = graph.get_node(src)
            tgt_entity = graph.get_node(tgt)
            src_name = src_entity["title"] if src_entity else src
            tgt_name = tgt_entity["title"] if tgt_entity else tgt
            print(f"    {dim(src_name)} → {dim(tgt_name)}")
        print()

    elif cmd == "dot":
      print(export_dot(graph))

    elif cmd == "dump":
      print()
      for e in graph.entities:
        print_entity(e, indent=2)
        print()

    else:
      print(f"  {yellow('Unknown command:')} {cmd}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
  args = sys.argv[1:]

  if not GRAPH_PATH.exists():
    print(f"\n  {red('No graph file found at')} {GRAPH_PATH}")
    print(f"  {dim('Run scripts/test-entities.py first to generate the graph.')}\n")
    sys.exit(1)

  data = json.loads(GRAPH_PATH.read_text())
  graph = EntityGraph(data)

  if "--stats" in args:
    print_stats(graph)
    return

  if "--dump" in args:
    print()
    for e in graph.entities:
      print_entity(e, indent=2)
      print()
    return

  if "--find" in args:
    idx = args.index("--find")
    query = args[idx + 1] if idx + 1 < len(args) else ""
    if not query:
      print(f"  {yellow('Usage: --find <query>')}")
      sys.exit(1)
    results = graph.find(query)
    print()
    for e in results:
      print_entity(e, indent=2)
      print()
    return

  if "--node" in args:
    idx = args.index("--node")
    node_id = args[idx + 1] if idx + 1 < len(args) else ""
    if not node_id:
      print(f"  {yellow('Usage: --node <source_id>')}")
      sys.exit(1)
    print_node_detail(graph, node_id)
    return

  if "--type" in args:
    idx = args.index("--type")
    etype = args[idx + 1] if idx + 1 < len(args) else ""
    if not etype:
      print(f"  {yellow('Usage: --type <entity_type>')}")
      sys.exit(1)
    entities = graph._by_type.get(etype, [])
    if not entities:
      for t in graph._by_type:
        if etype in t:
          entities = graph._by_type[t]
          break
    print()
    for e in entities:
      print_entity(e, indent=2)
      print()
    return

  if "--dot" in args:
    print(export_dot(graph))
    return

  # Default: interactive mode
  print_stats(graph)
  interactive_repl(graph)


if __name__ == "__main__":
  main()
