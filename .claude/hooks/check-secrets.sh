#!/usr/bin/env bash
# PreToolUse (Edit|Write): blocks writing obvious secrets into tracked files.
# Exit 2 = block, and the message on stderr is shown to Claude.
set -euo pipefail

HOOK_INPUT=$(cat) python3 -c '
import json, os, re, sys

tool = json.loads(os.environ["HOOK_INPUT"]).get("tool_input", {})
path = tool.get("file_path", "")
text = tool.get("content") or tool.get("new_string") or ""

if path.endswith(".env.example"):
    sys.exit(0)  # placeholders only

patterns = {
    "private key": r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "AWS key": r"AKIA[0-9A-Z]{16}",
    "GitHub token": r"gh[pousr]_[A-Za-z0-9]{36,}",
    "Slack token": r"xox[baprs]-[A-Za-z0-9-]{10,}",
    "hard-coded JWT secret": r"JWT_SECRET\s*=\s*[\x27\x22]?[A-Za-z0-9_\-]{32,}",
    "hard-coded DB URL with password": r"postgres(ql)?(\+\w+)?://[^:\s/]+:[^@\s]{6,}@",
}
for name, rx in patterns.items():
    if re.search(rx, text):
        print(f"Blocked: looks like a {name} in {path}. Secrets belong in .env only.", file=sys.stderr)
        sys.exit(2)
'
