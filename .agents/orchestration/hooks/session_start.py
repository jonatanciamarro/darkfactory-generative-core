#!/usr/bin/env python3
"""Session-start hook for corporate-engineer and DarkFactory.

Injects essential context and active state into every session start.
"""

import sys
from pathlib import Path


def get_workspace_root() -> Path:
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / ".git").exists() or (parent / "pyproject.toml").exists() or (parent / "state.md").exists():
            return parent
    return Path.cwd()


def run_session_start_hook() -> None:
    root = get_workspace_root()
    state_file = root / "state.md"
    state_info = "Not found"
    if state_file.exists():
        try:
            content = state_file.read_text(encoding="utf-8", errors="ignore")
            for line in content.splitlines():
                if "Testes" in line or "Linter" in line or "Fase" in line or "Status" in line:
                    state_info = "Metrics synced from state.md"
                    break
        except OSError:
            pass

    welcome_lines = [
        "🟢 Corp-Pipeline Master Orchestrator: ACTIVE",
        "• Project: DarkFactory (Autonomous Cinema Documentary Pipeline)",
        f"• Framework: corporate-engineer (Python 3.10+ target py311)",
        f"• Living State: {state_info} (read state.md before acting)",
        "• Capability Intelligence: Registries loaded from .agents/orchestration/",
        "• Execution Standard: 6-Phase Corp-Pipeline with Shift-Left TDD & Pre-Flight Gates",
        "• Continuous Improvement: Ideas presented via [CORP-PIPELINE / IMPROVEMENT DETECTED]",
    ]

    hook_dir = str(Path(__file__).parent.resolve())
    if hook_dir not in sys.path:
        sys.path.insert(0, hook_dir)

    src_dir = str(root / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    try:
        try:
            from corporate_engineer.git_utils import generate_pr_url, get_current_branch
        except ImportError:
            from git_utils import generate_pr_url, get_current_branch

        branch = get_current_branch(root)
        if branch.startswith(("feat/", "fix/", "chore/", "refactor/")):
            pr_url = generate_pr_url(root)
            if pr_url:
                welcome_lines.append(f"• Active Feature Branch: {branch} (PR: {pr_url})")
            else:
                welcome_lines.append(f"• Active Feature Branch: {branch}")
    except Exception:
        pass

    border = "=" * 70
    print(f"\n{border}")
    for line in welcome_lines:
        print(f"  {line}")
    print(f"{border}\n")


if __name__ == "__main__":
    run_session_start_hook()
