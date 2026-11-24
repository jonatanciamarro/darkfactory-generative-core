#!/usr/bin/env python3
"""
secret_scanner.py - Pre-Flight Security & Secret Audit Scanner for Corporate Pipelines.
Scans files in git repository or specified path for exposed credentials, API keys,
private keys, and tokens, returning exit code 0 if clean, or exit code 1 with findings.
"""

import os
import re
import sys
from pathlib import Path

# High-confidence signature patterns for enterprise secrets
SECRET_PATTERNS = [
    ("Private Key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")),
    ("AWS Access Key ID", re.compile(r"(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}")),
    ("GitHub Personal Access Token", re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,}")),
    ("GitLab Personal Access Token", re.compile(r"glpat-[0-9a-zA-Z_\-]{20,}")),
    ("OpenAI API Key", re.compile(r"sk-(?:proj-|live-)?[a-zA-Z0-9]{32,}")),
    ("Anthropic API Key", re.compile(r"sk-ant-[a-zA-Z0-9]{32,}")),
    ("Google Gemini/Cloud API Key", re.compile(r"AIzaSy[A-Za-z0-9_\-]{33}")),
    ("Slack Token", re.compile(r"xox[baprs]-[0-9]{10,13}-[a-zA-Z0-9]{24,}")),
    ("Stripe API Key", re.compile(r"(?:sk|rk)_(?:live|test)_[0-9a-zA-Z]{24,}")),
    ("Generic Hardcoded Secret", re.compile(r"""(?i)(?:api_key|secret_key|client_secret|db_password|access_token)\s*[:=]\s*["']([A-Za-z0-9_\-\.\$]{16,})["']""")),
]

IGNORE_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__",
    ".pytest_cache", "dist", "build", "target", "bin", "obj", ".idea", ".vscode",
    "chrome_session", "data", "models"
}

IGNORE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".tar", ".gz",
    ".exe", ".dll", ".so", ".dylib", ".pyc", ".lock", ".svg", ".woff", ".woff2",
    ".onnx", ".bin", ".pt", ".pth", ".safetensors", ".mp4", ".mp3", ".wav"
}


def scan_file(file_path: Path) -> list[tuple[str, int, str]]:
    findings = []
    try:
        if file_path.stat().st_size > 1_000_000:
            return findings
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return findings

    lines = content.splitlines()
    for line_num, line in enumerate(lines, start=1):
        # Skip commented placeholders or documentation/test mock examples
        if any(dummy in line.lower() for dummy in ["your_api_key", "example", "<api_key>", "placeholder", "fake_", "xxx", "dummy", "test_key", "test_api_key", "mock"]):
            continue

        for rule_name, pattern in SECRET_PATTERNS:
            match = pattern.search(line)
            if match:
                # Mask matched secret for safe display
                matched_str = match.group(0)
                masked = matched_str[:4] + "*" * (len(matched_str) - 8) + matched_str[-4:] if len(matched_str) > 8 else "***"
                findings.append((rule_name, line_num, masked))
                break

    return findings


def scan_directory(target_dir: Path) -> dict[str, list[tuple[str, int, str]]]:
    all_findings = {}
    for root, dirs, files in os.walk(target_dir):
        # Exclude ignored directories in-place
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]

        for f in files:
            p = Path(root) / f
            if p.suffix.lower() in IGNORE_EXTENSIONS:
                continue

            findings = scan_file(p)
            if findings:
                all_findings[str(p.relative_to(target_dir))] = findings

    return all_findings


def main():
    target_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    print(f"🔒 Executando Corporate Pre-Flight Secret Scanner em: {target_dir.resolve()} ...")
    
    findings = scan_directory(target_dir)
    
    if not findings:
        print("✅ Pre-Flight Secret Scan PASS: Nenhum segredo ou credencial exposta foi detectada.")
        sys.exit(0)
    else:
        print("\n❌ 🔴 CRITICAL: Segredos detectados nos seguintes arquivos:")
        for file_path, items in findings.items():
            print(f"\n📄 {file_path}:")
            for rule_name, line_num, masked in items:
                print(f"   [Linha {line_num}] Tipo: {rule_name} | Valor mascarado: {masked}")
        
        print("\n🚫 Interrompendo pipeline: remova as credenciais hardcoded antes de prosseguir para o Gate 2.")
        sys.exit(1)


if __name__ == "__main__":
    main()
