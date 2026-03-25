"""
pipeline/alex_runner.py

Runs AlexJS (https://alexjs.com/) on text content to detect potentially
insensitive language.

run_alex(text) → dict with {warnings_count, warnings, [skipped]}

If Node/npx is not available, logs a warning and returns a zero-warning result
with skipped=True — the pipeline never crashes due to a missing AlexJS dependency.
"""

from __future__ import annotations

import json
import logging
import subprocess
import shutil
from typing import Optional

log = logging.getLogger("pipeline.alex_runner")


def run_alex(text: str) -> dict:
    """
    Run `npx alex --stdin` on the given text and parse warnings.

    Returns:
        {
            "warnings_count": int,
            "warnings": [{"line": int, "column": int, "message": str}, ...],
            "skipped": bool  # present and True only if alex was not available
        }

    Never raises — if alex is unavailable or fails, returns skipped result.
    """
    # Check npx availability first
    if not shutil.which("npx"):
        log.warning("alex_skip: npx not available; AlexJS check skipped")
        return {"warnings_count": 0, "warnings": [], "skipped": True}

    try:
        result = subprocess.run(
            ["npx", "--yes", "alex", "--stdin"],
            input=text,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        log.warning("alex_skip: npx binary not found")
        return {"warnings_count": 0, "warnings": [], "skipped": True}
    except subprocess.TimeoutExpired:
        log.warning("alex_timeout: AlexJS timed out after 30s")
        return {"warnings_count": 0, "warnings": [], "skipped": True}
    except Exception as exc:  # pragma: no cover
        log.warning("alex_error: %s", exc)
        return {"warnings_count": 0, "warnings": [], "skipped": True}

    # alex writes warnings to stderr and exits non-zero if warnings found.
    # Parse the stderr output to extract warning messages.
    warnings = _parse_alex_output(result.stderr or result.stdout or "")

    return {
        "warnings_count": len(warnings),
        "warnings": warnings,
    }


def _parse_alex_output(output: str) -> list:
    """
    Parse alex CLI output into a list of warning dicts.

    Alex output format (VFile compatible):
      <stdin>
        N:M  warning  <message>  <rule>
      N warnings
    """
    warnings = []
    for line in output.splitlines():
        line = line.strip()
        # Lines with warnings look like: "  1:3  warning  Don't use "..."  rule-name"
        if "warning" in line and ":" in line:
            parts = line.split(None, 3)  # split on whitespace, max 4 parts
            if len(parts) >= 3 and ":" in parts[0]:
                try:
                    loc = parts[0]
                    line_num_str, col_str = loc.split(":")
                    line_num = int(line_num_str)
                    col = int(col_str)
                    message = parts[2] if len(parts) > 2 else line
                    if len(parts) > 3:
                        message = parts[3]
                    warnings.append({
                        "line": line_num,
                        "column": col,
                        "message": message.strip(),
                    })
                except (ValueError, IndexError):
                    # If we can't parse the line, still record it
                    warnings.append({"line": 0, "column": 0, "message": line})
    return warnings
