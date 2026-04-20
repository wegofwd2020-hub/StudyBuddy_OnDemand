#!/bin/bash
# PostToolUse hook: lightweight AST syntax check on Alembic migration files.
# Catches the class of errors that would otherwise blow up `alembic upgrade head`
# (unclosed strings, missing imports surfaced at parse time, etc).
# Non-blocking — always exits 0. The warning surfaces via stderr if parse fails.

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_response.filePath // empty')

if [[ -z "$FILE_PATH" ]]; then
  exit 0
fi

if [[ "$FILE_PATH" != *backend/alembic/versions/*.py ]]; then
  exit 0
fi

if command -v python3 >/dev/null 2>&1; then
  python3 -c "import ast, sys; ast.parse(open(sys.argv[1]).read())" "$FILE_PATH" 2>&1 || {
    echo "⚠️  Migration syntax error in $FILE_PATH — alembic will fail on upgrade" >&2
  }
fi

exit 0
