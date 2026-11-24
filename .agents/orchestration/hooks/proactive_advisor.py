#!/usr/bin/env python3
"""
proactive_advisor.py - Antigravity PreInvocation Hook for Proactive Intelligence.
Executes before the model turn, anticipating intent, domains, risks,
and providing the 2-steps-ahead tactical plan + 1-Click PR link.
Contract: Reads JSON on stdin, outputs valid protojson on stdout.
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


def run_proactive_advisor_hook() -> None:
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
        from corporate_engineer.orchestrator.hooks_runner import (
            generate_pre_invocation_hook_output,
        )

        output = generate_pre_invocation_hook_output(raw_input_data, workspace_root=root)
    except Exception as e:  # noqa: BLE001
        output = {
            "injectSteps": [
                {
                    "systemMessage": {
                        "systemMessage": f"⚠️ [PROACTIVE ADVISOR WARNING]: Fallback ativo ({e})"
                    }
                }
            ]
        }

    sys.stdout.write(json.dumps(output, ensure_ascii=False))
    sys.stdout.flush()


if __name__ == "__main__":
    run_proactive_advisor_hook()
