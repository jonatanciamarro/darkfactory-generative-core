#!/usr/bin/env python3
"""
session_start.py - Antigravity Lifecycle Hook for Corp-Pipeline Initialization.
Executes on SessionStart event, verifies state.md, installs git hooks,
audits storage health, and injects orchestrator guidance.
Contract: Reads JSON on stdin, outputs valid protojson on stdout.
"""

from __future__ import annotations

import json
import shutil
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


def run_session_start_hook() -> None:
    # Read stdin safely if piped
    try:
        if not sys.stdin.isatty():
            raw_input = sys.stdin.read()
            if raw_input.strip():
                _ = json.loads(raw_input)
    except (json.JSONDecodeError, OSError):
        pass

    root = get_workspace_root()
    venv_site = root / 'venv' / 'Lib' / 'site-packages'
    if venv_site.exists():
        import site
        site.addsitedir(str(venv_site))
    state_file = root / "state.md"

    # Extract high-level summary from state.md if present
    state_info = "State file present" if state_file.exists() else "No state.md found"
    if state_file.exists():
        try:
            content = state_file.read_text(encoding="utf-8", errors="ignore")
            for line in content.splitlines():
                if "Testes (Pytest" in line or "Linter" in line:
                    state_info = "Metrics synced from state.md"
                    break
        except OSError:
            pass

    # Ensure src is in sys.path
    src_dir = str(root / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    # 1. Instalação automática de Git hooks locais (pre-commit e pre-push)
    git_hooks_status = "Git Hooks ativos"
    try:
        from corporate_engineer.quality.git_hooks_installer import install_git_hooks

        if install_git_hooks(workspace_root=root):
            git_hooks_status = "Git Hooks pre-commit & pre-push instalados e ativos"
    except Exception:  # noqa: BLE001
        git_hooks_status = "Git Hooks locais não configurados"

    # 2. Diagnóstico de Armazenamento
    disk_info = ""
    try:
        _total, _used, free = shutil.disk_usage(root)
        free_gb = free / (1024**3)
        disk_info = f" • Armazenamento Livre: {free_gb:.1f} GB"
    except Exception:  # noqa: BLE001, S110
        pass

    welcome_lines = [
        "🟢 Corp-Pipeline Master Orchestrator: ACTIVE & PROACTIVE",
        f"• Framework: corporate-engineer (Python 3.10+ target py311){disk_info}",
        f"• Living State: {state_info} (read state.md before acting)",
        f"• Local Automation: {git_hooks_status}",
        "• Capability Intelligence: Registries loaded from .agents/orchestration/",
        "• Proactive Engine (2 Passos à Frente): PreInvocation, PreToolUse & PostToolUse hooks habilitados",
        "• Execution Standard: 6-Phase Corp-Pipeline with Shift-Left TDD & Pre-Flight Gates",
        "• Continuous Improvement: Ideas presented via [CORP-PIPELINE / IMPROVEMENT DETECTED]",
    ]

    try:
        from corporate_engineer.git_utils import generate_pr_url, get_current_branch

        branch = get_current_branch(root)
        if branch.startswith(("feat/", "fix/", "chore/", "refactor/")):
            pr_info = generate_pr_url(repo_path=root, branch=branch, ensure_pushed=False)
            welcome_lines.append(f"• Pre-filled 1-Click PR URL: {pr_info['url']}")
    except Exception:  # noqa: BLE001, S110
        pass

    welcome_msg = "\n".join(welcome_lines)

    output = {
        "injectSteps": [
            {
                "systemMessage": {
                    "systemMessage": welcome_msg
                }
            }
        ]
    }

    # Write pure JSON to stdout
    sys.stdout.write(json.dumps(output, ensure_ascii=False))
    sys.stdout.flush()


if __name__ == "__main__":
    run_session_start_hook()
