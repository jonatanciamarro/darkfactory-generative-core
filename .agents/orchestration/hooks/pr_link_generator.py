#!/usr/bin/env python3
"""
pr_link_generator.py - Antigravity Lifecycle Hook for Automatic Pre-Filled GitHub PR Links.
Executes on PreInvocation, PostToolUse or direct invocation, detecting active feature branches
and injecting the 1-click GitHub PR URL with pre-filled title and body.
Contract: Reads JSON on stdin, outputs valid protojson on stdout.
"""

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


def run_pr_link_hook() -> None:
    # Read stdin safely if piped
    try:
        if not sys.stdin.isatty():
            raw_input = sys.stdin.read()
            if raw_input.strip():
                _ = json.loads(raw_input)
    except (json.JSONDecodeError, OSError):
        pass

    root = get_workspace_root()

    # Ensure src is in python path
    src_dir = str(root / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    try:
        from corporate_engineer.git_utils import generate_pr_url, get_current_branch

        branch = get_current_branch(root)
        # Only inject if on a feature or fix branch
        if branch.startswith(("feat/", "fix/", "chore/", "refactor/")):
            info = generate_pr_url(repo_path=root, branch=branch, ensure_pushed=True)
            push_status = "✅ Sincronizado no origin" if info.get("pushed") else "⚠️  Local apenas"
            msg = (
                "🔗 [HOOK / PRE-FILLED GITHUB PR LINK ACTIVE]\n"
                f"• Branch: {info['branch']} ➔ {info['base']}\n"
                f"• Ticket: {info['ticket_id']}\n"
                f"• Título da PR: {info['title']}\n"
                f"• Push Status: {push_status}\n"
                f"• 1-Click URL: {info['url']}\n"
                "• Invariante Mandatória Always-On: O push da branch para o remote origin (git push -u origin <branch>) "
                "deve SEMPRE ocorrer antes de gerar ou fornecer a URL ao usuário, garantindo que o link do GitHub nunca abra em 404."
            )
            output = {
                "injectSteps": [
                    {
                        "systemMessage": {
                            "systemMessage": msg
                        }
                    }
                ]
            }
        else:
            output = {}
    except Exception as e:  # noqa: BLE001
        output = {"error": str(e)}

    sys.stdout.write(json.dumps(output, ensure_ascii=False))
    sys.stdout.flush()


if __name__ == "__main__":
    run_pr_link_hook()
