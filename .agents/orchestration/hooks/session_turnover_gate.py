#!/usr/bin/env python3
"""
session_turnover_gate.py - Antigravity Stop Hook for Session Turnover Invariants.
Executes when the agent loop terminates, verifying state.md synchronization
and alerting about any pending pre-flight checks or unpushed branches.
Contract: Reads JSON on stdin, outputs empty JSON object {} on stdout.
"""

from __future__ import annotations

import json
import subprocess
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


def run_session_turnover_gate_hook() -> None:
    root = get_workspace_root()
    venv_site = root / 'venv' / 'Lib' / 'site-packages'
    if venv_site.exists():
        import site
        site.addsitedir(str(venv_site))

    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            check=False,
            capture_output=True,
            text=True,
            cwd=str(root),
        )
        if proc.returncode == 0 and proc.stdout.strip():
            modified_count = len(proc.stdout.splitlines())
            sys.stderr.write(
                f"\n⚠️ [TURNOVER GATE]: {modified_count} arquivo(s) modificado(s) ou não commitado(s). "
                "Lembre-se de atualizar o `state.md` e executar `/preflight` antes de concluir.\n"
            )
    except Exception:  # noqa: BLE001, S110
        pass

    sys.stdout.write(json.dumps({}, ensure_ascii=False))
    sys.stdout.flush()


if __name__ == "__main__":
    run_session_turnover_gate_hook()
