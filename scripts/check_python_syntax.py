#!/usr/bin/env python3
"""
Check Python syntax errors across all Python files in the skills directory.

Usage:
    python scripts/check_python_syntax.py
    python scripts/check_python_syntax.py --path skills/browser
    python scripts/check_python_syntax.py --verbose
"""

import argparse
import os
import py_compile
import sys
from pathlib import Path
from typing import List, Tuple


def check_file(filepath: Path, verbose: bool = False) -> Tuple[bool, str]:
    """
    Check a single Python file for syntax errors.
    
    Returns:
        (is_valid, error_message)
    """
    try:
        py_compile.compile(str(filepath), doraise=True)
        if verbose:
            return True, f"✓ {filepath}"
        return True, ""
    except py_compile.PyCompileError as e:
        error_msg = str(e).replace(str(filepath), str(filepath.relative_to(Path.cwd())))
        return False, f"✗ {filepath.relative_to(Path.cwd())}: {error_msg}"
    except Exception as e:
        return False, f"✗ {filepath.relative_to(Path.cwd())}: Unexpected error - {e}"


def find_python_files(directory: Path, exclude_dirs: List[str] = None) -> List[Path]:
    """
    Find all Python files in a directory tree.
    
    Args:
        directory: Root directory to search
        exclude_dirs: List of directory names to exclude (e.g., ['__pycache__', '.git'])
    
    Returns:
        List of Python file paths
    """
    if exclude_dirs is None:
        exclude_dirs = ['__pycache__', '.git', '.venv', 'venv', 'node_modules', '.pytest_cache']
    
    python_files = []
    for root, dirs, files in os.walk(directory):
        # Remove excluded directories from dirs list to prevent walking into them
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if file.endswith('.py'):
                filepath = Path(root) / file
                python_files.append(filepath)
    
    return sorted(python_files)


def main():
    parser = argparse.ArgumentParser(
        description="Check Python syntax errors in skills directory"
    )
    parser.add_argument(
        '--path',
        type=str,
        default='skills',
        help='Path to directory or file to check (default: skills)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show all files checked, including successful ones'
    )
    parser.add_argument(
        '--exclude',
        nargs='+',
        default=['__pycache__', '.git', '.venv', 'venv'],
        help='Directories to exclude (default: __pycache__ .git .venv venv)'
    )
    
    args = parser.parse_args()
    
    # Determine what to check
    check_path = Path(args.path)
    if not check_path.exists():
        print(f"Error: Path '{check_path}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    # Collect files to check
    if check_path.is_file():
        if check_path.suffix != '.py':
            print(f"Error: '{check_path}' is not a Python file", file=sys.stderr)
            sys.exit(1)
        files_to_check = [check_path]
    else:
        files_to_check = find_python_files(check_path, exclude_dirs=args.exclude)
    
    if not files_to_check:
        print(f"No Python files found in '{check_path}'")
        sys.exit(0)
    
    # Check all files
    errors = []
    checked = 0
    
    print(f"Checking {len(files_to_check)} Python file(s)...\n")
    
    for filepath in files_to_check:
        is_valid, message = check_file(filepath, verbose=args.verbose)
        checked += 1
        
        if is_valid:
            if args.verbose:
                print(message)
        else:
            errors.append(message)
            print(message)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Checked: {checked} file(s)")
    print(f"Errors:  {len(errors)} file(s)")
    
    if errors:
        print(f"\n{'='*60}")
        print("ERRORS FOUND:")
        for error in errors:
            print(f"  {error}")
        sys.exit(1)
    else:
        print("\n✓ All Python files have valid syntax!")
        sys.exit(0)


if __name__ == '__main__':
    main()
