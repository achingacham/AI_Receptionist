#!/usr/bin/env bash
# PostToolUse hook: lint-fix and format a Python file after Claude edits it.
# Unfixable lint errors exit 2 so they are fed back to Claude.

f=$(jq -r '.tool_response.filePath // .tool_input.file_path // empty')
[[ "$f" == *.py && -f "$f" ]] || exit 0

cd "$CLAUDE_PROJECT_DIR" || exit 0
ruff=.venv/bin/ruff
[ -x "$ruff" ] || ruff=ruff

"$ruff" format --quiet "$f"
if ! out=$("$ruff" check --fix --quiet "$f" 2>&1); then
  echo "ruff found issues in $f:" >&2
  echo "$out" >&2
  exit 2
fi
