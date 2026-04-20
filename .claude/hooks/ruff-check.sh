#!/bin/bash
# PostToolUse hook: run `ruff check --fix` on Python files under backend/
# Non-blocking — always exits 0 so a lint finding never interrupts the edit.
# Benchmarked ~1.4s on backend/main.py (host ruff).

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_response.filePath // empty')

if [[ -z "$FILE_PATH" ]]; then
  exit 0
fi

if [[ "$FILE_PATH" != *backend/*.py ]]; then
  exit 0
fi

if command -v ruff >/dev/null 2>&1; then
  ruff check --fix "$FILE_PATH" 2>&1 || true
fi

exit 0
