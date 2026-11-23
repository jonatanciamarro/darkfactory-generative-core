#!/usr/bin/env python3
"""Hook for pre-invocation to generate and print pull request links for current branch."""

import sys
from pathlib import Path


def get_workspace_root() -> Path:
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / ".git").exists() or (parent / "pyproject.toml").exists() or (parent / "state.md").exists():
            return parent
    return Path.cwd()


def run_pr_link_hook() -> None:
    root = get_workspace_root()

    # Try importing from local hook dir or sys.path
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
        # Only inject if on a feature or fix branch
        if branch.startswith(("feat/", "fix/", "chore/", "refactor/")):
            pr_url = generate_pr_url(root)
            if pr_url:
                print(
                    f"\n🔗 [CORP-PIPELINE PR]: Sincronize sua branch e crie o Pull Request em:\n   👉 {pr_url}\n"
                )
    except Exception:
        # Hooks must never crash the main process
        pass


if __name__ == "__main__":
    run_pr_link_hook()
