#!/usr/bin/env bash
# PostToolUse (Edit|Write): formats the edited file with the project's formatter. Never blocks.
set -uo pipefail

file=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))')
root="$CLAUDE_PROJECT_DIR"
export PATH="$HOME/.local/bin:$HOME/.local/node/bin:$PATH"

case "$file" in
  "$root"/apps/api/*.py|"$root"/scripts/*.py)
    (cd "$root/apps/api" && uv run --quiet ruff format "$file" >/dev/null 2>&1 \
      && uv run --quiet ruff check --fix --quiet "$file" >/dev/null 2>&1) ;;
  "$root"/apps/mobile/*.ts|"$root"/apps/mobile/*.tsx)
    (cd "$root/apps/mobile" && npx --no-install eslint --fix "$file" >/dev/null 2>&1) ;;
esac
exit 0
