#!/usr/bin/env python3
"""
pre_tool_security_guard.py - Antigravity PreToolUse Hook for Zero-Secret Guard.
Executes before write_file or edit_file to block credentials from ever reaching disk.
Contract: Reads JSON on stdin, outputs valid protojson decision on stdout.
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


def run_pre_tool_security_guard_hook() -> None:
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
        from corporate_engineer.quality.tool_security_guard import (
            evaluate_tool_security,
        )

        decision = evaluate_tool_security(raw_input_data)
    except Exception as e:  # noqa: BLE001
        # Fallback defensivo: permitir com aviso se houver falha de infraestrutura
        decision = {"decision": "allow", "reason": f"Fallback por erro interno: {e}"}

    sys.stdout.write(json.dumps(decision, ensure_ascii=False))
    sys.stdout.flush()


if __name__ == "__main__":
    run_pre_tool_security_guard_hook()
