#!/usr/bin/env python3
"""Stop hook: enforce Corporate Git Governance, Branch Protection and Pre-Exit Verification.

Contract: Stop -> input has executionNum, terminationReason, fullyIdle, error.
          Output: { "decision": "continue"|"stop", "reason": "..." }
"""
import json
import os
import subprocess
import sys


# Reasons where we should NOT force continuation
TERMINAL_REASONS = {
    "USER_CANCELED",
    "MAX_TOKEN_BUDGET_EXCEEDED",
    "MAX_FORCED_INVOCATIONS",
    "TERMINAL_CUSTOM_HOOK",
}


def find_project_root() -> str:
    """Find the project root by locating package.json or walking up."""
    current = os.path.dirname(os.path.abspath(__file__))
    while current and os.path.dirname(current) != current:
        if os.path.isfile(os.path.join(current, "package.json")) or os.path.isdir(os.path.join(current, ".git")):
            return current
        current = os.path.dirname(current)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(script_dir))


def main() -> None:
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            print(json.dumps({"decision": "stop"}))
            return
        payload = json.loads(raw_input)
    except (json.JSONDecodeError, Exception):
        print(json.dumps({"decision": "stop"}))
        return

    termination_reason = payload.get("terminationReason", "")
    execution_num = payload.get("executionNum", 0)

    # Never override user cancellation or hard limits
    if termination_reason in TERMINAL_REASONS:
        print(json.dumps({"decision": "stop"}))
        return

    # Safety: don't loop forever — cap forced continuations
    if execution_num > 10:
        print(
            json.dumps(
                {
                    "decision": "stop",
                    "reason": "Reached max execution count (10). Stopping.",
                }
            )
        )
        return

    project_root = find_project_root()
    if execution_num < 3:
        try:
            # 1. Identificar branch ativa
            branch_proc = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=5,
            )
            current_branch = branch_proc.stdout.strip()

            # 2. Verificar arquivos modificados ou untracked
            status_proc = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=5,
            )
            has_uncommitted = bool(status_proc.stdout and status_proc.stdout.strip())

            # 3. Regra Corporativa Zero-Main: Proibir commits na main/master
            if current_branch in ["main", "master"]:
                if has_uncommitted:
                    reason = (
                        f"⚠️ [HOOK GATE - VIOLAÇÃO CORPORATIVA] Você está na branch '{current_branch}' com alterações pendentes. "
                        "Em conformidade com AGENTS.md e GEMINI.md, é TERMINANTEMENTE PROIBIDO commitar direto na main/master. "
                        "Crie uma branch de feature: 'git checkout -b feat/<ticket>-<slug>' e realize o commit nela."
                    )
                    print(json.dumps({"decision": "continue", "reason": reason}))
                    return

            # 4. Verificar commits não sincronizados com o repositório remoto
            target_upstream = f"origin/{current_branch}" if current_branch else "origin/main"
            cherry_proc = subprocess.run(
                ["git", "cherry", "-v", target_upstream],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=5,
            )
            has_unpushed = bool(cherry_proc.stdout and cherry_proc.stdout.strip())

            if has_uncommitted or has_unpushed:
                issues = []
                if has_uncommitted:
                    issues.append("arquivos não commitados no working tree")
                if has_unpushed:
                    # Check if remote is reachable before enforcing remote push
                    is_reachable = False
                    try:
                        net_check = subprocess.run(
                            ["git", "ls-remote", "--exit-code", "origin"],
                            cwd=project_root,
                            capture_output=True,
                            timeout=2,
                        )
                        is_reachable = (net_check.returncode == 0)
                    except Exception:
                        is_reachable = False
                    if is_reachable:
                        issues.append(f"commits locais pendentes de push para {target_upstream}")
                if issues:
                    reason = (
                        f"⚠️ [HOOK GATE - GOVERNANÇA CORPORATIVA] Detectado: {', '.join(issues)}. "
                        f"Na branch '{current_branch}', conclua os commits semânticos atômicos e execute "
                        f"'git push origin {current_branch}' para disponibilizar o Pull Request corporativo."
                    )
                    print(json.dumps({"decision": "continue", "reason": reason}))
                    return
        except Exception:
            pass

    # Normal completion — allow stop
    print(json.dumps({"decision": "stop"}))


if __name__ == "__main__":
    main()
