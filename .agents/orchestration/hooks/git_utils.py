"""
Git utilities and pre-filled GitHub Pull Request URL generator for Corporate Pipelines.
"""

import re
import subprocess
import urllib.parse
from pathlib import Path


def extract_github_repo_slug(remote_url: str) -> str:
    """Extract owner/repo slug from HTTPS or SSH Git remote URL."""
    match = re.search(r"github\.com[:/]([^/]+)/([^/\.]+)", remote_url)
    if match:
        owner, repo = match.group(1), match.group(2)
        return f"{owner}/{repo}"
    return "ciamarrojonatan-droid/darkfactory"


def get_current_branch(repo_path: Path | str = ".") -> str:
    """Retrieve the current active Git branch name."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            cwd=str(Path(repo_path).resolve()),
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass

    # Fallback to reading .git/HEAD directly
    head_file = Path(repo_path) / ".git" / "HEAD"
    if head_file.exists():
        try:
            content = head_file.read_text(encoding="utf-8").strip()
            if content.startswith("ref: refs/heads/"):
                return content.replace("ref: refs/heads/", "").strip()
        except OSError:
            pass

    return "main"


def get_remote_url(repo_path: Path | str = ".", remote_name: str = "origin") -> str:
    """Get the fetch URL for the specified Git remote."""
    try:
        proc = subprocess.run(
            ["git", "remote", "get-url", remote_name],
            check=False,
            capture_output=True,
            text=True,
            cwd=str(Path(repo_path).resolve()),
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return "https://github.com/ciamarrojonatan-droid/darkfactory.git"


def find_pr_document(repo_path: Path | str = ".", branch: str = "") -> Path | None:
    """Locate the most relevant or latest PR markdown document in docs/pull_requests/."""
    pr_dir = Path(repo_path) / "docs" / "pull_requests"
    if not pr_dir.exists():
        return None

    pr_files = sorted(pr_dir.glob("PR-*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not pr_files:
        return None

    # If branch specifies ticket ID, e.g. IMP-0006 or FEAT-01
    ticket_match = re.search(r"([A-Z]+-\d+)", branch, re.IGNORECASE)
    if ticket_match:
        ticket = ticket_match.group(1).upper()
        for f in pr_files:
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
                if ticket in content:
                    return f
            except OSError:
                continue

    # Return latest PR doc as default
    return pr_files[0]


def generate_pr_url(
    repo_path: Path | str = ".",
    branch: str | None = None,
    base: str = "main",
    pr_doc_path: Path | str | None = None,
    repo_slug: str | None = None,
) -> dict[str, str]:
    """Generate a 1-click pre-filled GitHub Pull Request creation URL with title and body."""
    resolved_path = Path(repo_path).resolve()
    active_branch = branch or get_current_branch(resolved_path)

    if not repo_slug:
        remote_url = get_remote_url(resolved_path)
        slug = extract_github_repo_slug(remote_url)
    else:
        slug = repo_slug

    doc = (
        Path(pr_doc_path).resolve()
        if pr_doc_path
        else find_pr_document(resolved_path, active_branch)
    )

    title = f"feat: {active_branch}"
    body = f"Pull Request for branch `{active_branch}`."
    ticket_id = "N/A"

    if doc and doc.exists():
        try:
            content = doc.read_text(encoding="utf-8")
            body = content
            lines = content.splitlines()
            for line in lines:
                if line.startswith("# Pull Request:"):
                    title = line.replace("# Pull Request:", "").strip()
                    break
                elif line.startswith("# "):
                    title = line.replace("# ", "").strip()
                    break

            ticket_match = re.search(r"`([A-Z]+-\d+)`", content)
            if ticket_match:
                ticket_id = ticket_match.group(1)
        except OSError:
            pass
    else:
        # Try reading latest commit message
        try:
            proc = subprocess.run(
                ["git", "log", "-1", "--pretty=%s"],
                check=False,
                capture_output=True,
                text=True,
                cwd=str(resolved_path),
            )
            if proc.returncode == 0 and proc.stdout.strip():
                title = proc.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass

    params = urllib.parse.urlencode(
        {
            "quick_pull": "1",
            "title": title,
            "body": body,
        }
    )

    pr_url = f"https://github.com/{slug}/compare/{base}...{active_branch}?{params}"

    return {
        "branch": active_branch,
        "base": base,
        "title": title,
        "ticket_id": ticket_id,
        "pr_doc": str(doc) if doc else "",
        "url": pr_url,
    }
