#!/usr/bin/env python3
"""
Analyze Python files by line count and suggest/perform splits.

Finds files exceeding a threshold (default 300 lines) and provides
suggestions for splitting them into smaller modules.

Usage:
    python scripts/analyze-and-split.py                    # Analyze and report
    python scripts/analyze-and-split.py --threshold 500   # Custom threshold
    python scripts/analyze-and-split.py --split            # Auto-split files
    python scripts/analyze-and-split.py --top 10           # Show top N files
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .analyze import ROOT, analyze_files, print_report
from .split import split_file


def main() -> int:
  """Main entry point."""
  parser = argparse.ArgumentParser(
    description="Analyze Python files and suggest splits",
    formatter_class=argparse.RawDescriptionHelpFormatter,
  )
  parser.add_argument(
    "--threshold",
    type=int,
    default=500,
    help="Line count threshold (default: 500)",
  )
  parser.add_argument(
    "--top",
    type=int,
    default=None,
    help="Show only top N files",
  )
  parser.add_argument(
    "--split",
    action="store_true",
    help="Auto-split files by sections",
  )
  parser.add_argument(
    "--split-classes",
    action="store_true",
    help="Auto-split files by classes",
  )
  parser.add_argument(
    "--file",
    type=str,
    default=None,
    help="Split a specific file (relative path)",
  )
  parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Show what would be split without actually splitting",
  )
  parser.add_argument(
    "--verbose",
    action="store_true",
    help="Show detailed analysis",
  )

  args = parser.parse_args()

  # Handle single file split
  if args.file:
    file_path = ROOT / args.file
    if not file_path.exists():
      print(f"Error: File not found: {file_path}", file=sys.stderr)
      return 1

    method = "classes" if args.split_classes else "sections"
    try:
      created = split_file(file_path, method=method, dry_run=args.dry_run, verbose=args.verbose)
      if args.dry_run:
        print("\n💡 Run without --dry-run to perform the split")
      else:
        print(f"\n✅ Split {file_path} into {len(created) + 1} files:")
        print(f"   - {file_path} (updated)")
        for f in created:
          print(f"   - {f}")
    except Exception as e:
      print(f"Error splitting file: {e}", file=sys.stderr)
      import traceback

      if args.verbose:
        traceback.print_exc()
      return 1
    return 0

  # Handle bulk split
  if args.split or args.split_classes:
    results = analyze_files(threshold=args.threshold, top_n=args.top)
    if not results:
      print("No files to split!")
      return 0

    method = "classes" if args.split_classes else "sections"
    print(f"\n⚠️  About to split {len(results)} files using method: {method}")
    if not args.dry_run:
      response = input("Continue? (yes/no): ")
      if response.lower() != "yes":
        print("Cancelled.")
        return 0

    for result in results:
      file_path = ROOT / result["file"]
      try:
        created = split_file(file_path, method=method, dry_run=args.dry_run)
        if not args.dry_run:
          print(f"✅ Split {file_path} into {len(created) + 1} files")
      except Exception as e:
        print(f"❌ Error splitting {file_path}: {e}", file=sys.stderr)

    return 0

  # Default: analyze and report
  results = analyze_files(threshold=args.threshold, top_n=args.top)
  print_report(results)

  return 0


if __name__ == "__main__":
  sys.exit(main())
