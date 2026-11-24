#!/usr/bin/env python3
"""
post_tool_auto_healer.py - Antigravity PostToolUse Hook for Auto-Healing & Blast Radius.
Executes after write_file or edit_file to auto-repair AST violations and compute impact.
Contract: Reads JSON on stdin, outputs empty JSON object {} on stdout.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def get_workspace_root() -> Path:
    """Resolve repository workspace root from cwd or script location."""
    current = Path.cwd().resolve()
    if current.name == ".agents":
        return current.parent
    for parent in [current] + list(current.parents):
        if (parent / "state.md").exists() or (parent / ".git").exists():
            return parent
    return current


def run_post_tool_auto_healer_hook() -> None:
    raw_input_data: dict = {}
    try:
        if not sys.stdin.isatty():
            content = sys.stdin.read()
            if content.strip():
                raw_input_data = json.loads(content)
    except (json.JSONDecodeError, OSError):
        raw_input_data = {}

    root = get_workspace_root()
    src_dir = str(root / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    try:
        from corporate_engineer.quality.tool_auto_healer import handle_post_tool_use

        output = handle_post_tool_use(raw_input_data, workspace_root=root)
    except Exception:  # noqa: BLE001
        output = {}

    sys.stdout.write(json.dumps(output, ensure_ascii=False))
    sys.stdout.flush()


if __name__ == "__main__":
    run_post_tool_auto_healer_hook()
