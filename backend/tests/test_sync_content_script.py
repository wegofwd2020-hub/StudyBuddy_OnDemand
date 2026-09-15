"""`sync-content.sh`'s remote block must not let a command eat its own script.

The cache-invalidation step (#748) is delivered to the VPS as:

    ssh "$TARGET" 'bash -s' <<'REMOTE'
    ...
    REMOTE

so **the script is stdin**. Any command inside it that reads stdin and is not
redirected consumes the REST OF THE SCRIPT. `docker compose exec -T` does
exactly that. Execution stops silently at the first such command, the remaining
lines are swallowed as that command's input, and -- this is what makes it
invisible -- **bash still exits 0**.

Measured against the live demo on 2026-09-10: step 5 printed no keys, returned
an empty string, and landed in the `''|*[!0-9]*)` branch, so every run reported
"cache invalidation failed" while clearing nothing. Adding `</dev/null` to each
`docker compose exec` made the same block run to completion.

Why this matters beyond a cosmetic error message: `get_content_file` caches
every content JSON under `content:{curriculum_id}:{unit_id}:{filename}` with a
3600s TTL. Without invalidation a sync changes nothing a student sees for up to
an hour -- and keys expire individually, so the box serves a MIX of old and new
content in the meantime. That is performance rule #7 in CLAUDE.md, and the step
that implements it was a no-op.
"""

from __future__ import annotations

import os
import re
import subprocess
import textwrap

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPT = os.path.join(os.path.dirname(os.path.dirname(_HERE)), "scripts", "demo", "sync-content.sh")

# The `api` container bind-mounts only `./backend` at `/app`, so the repo's
# `scripts/` tree is not present there and these checks cannot read the file.
# CI is the gate that matters and runs `pytest tests/` from `backend/` on a full
# checkout, where the path resolves -- so a skip here never lets the guard go
# unrun before a merge. It is an explicit skip rather than a silent pass so that
# "0 offenders" can never mean "0 files examined".
_NO_CHECKOUT = not os.path.isfile(_SCRIPT)
_needs_checkout = pytest.mark.skipif(
    _NO_CHECKOUT,
    reason=f"{_SCRIPT} not present (running inside a container that mounts only ./backend)",
)

# Commands that read stdin when it is not redirected. `docker compose exec -T`
# is the one that bit us; `ssh` and `redis-cli` are here because they have the
# same property and would fail the same way inside a `bash -s` payload.
# NOTE: no leading `\b` before the alternation -- `${DC[@]}` starts with `$`,
# a non-word character, so a word boundary cannot match there when the previous
# character is a quote. That mistake made the detector silently match nothing.
_STDIN_READERS = re.compile(r"(\bdocker\s+compose\s+exec|\$\{DC\[@\]\}\"?\s+exec|\bssh\b)")

# Any form of stdin redirection: `</dev/null`, `< /dev/null`, `<<EOF`, `<file`.
_REDIRECTS_STDIN = re.compile(r"<")


def _remote_blocks(text: str) -> list[tuple[str, str]]:
    """Every `<<'TAG' ... TAG` heredoc that is piped into a remote shell.

    Returns (tag, body) pairs. Only blocks fed to `bash -s` count -- an
    ordinary local heredoc is not at risk, because its consumer is not also
    reading the script itself.
    """
    blocks = []
    # `[^\n]*` after the tag matters: the real call ends the line with
    # ` 2>/dev/null`, and requiring a bare newline there found nothing at all.
    for m in re.finditer(r"bash -s'[^\n]*<<'(\w+)'[^\n]*\n(.*?)\n\1\b", text, re.DOTALL):
        blocks.append((m.group(1), m.group(2)))
    return blocks


def test_the_mechanism_is_real_and_the_fix_works():
    """Reproduce the bug class with no docker, ssh or network.

    `cat` stands in for `docker compose exec -T`: both read stdin. This is the
    control for the static check below -- without it, a passing lint rule would
    prove only that a string is absent, not that its absence mattered.
    """

    def run(body: str) -> str:
        return subprocess.run(
            ["bash", "-s"],
            input=textwrap.dedent(body),
            capture_output=True,
            text=True,
            timeout=30,
        )

    eaten = run(
        """
        echo BEFORE
        cat > /dev/null
        echo AFTER
        """
    )
    # The tail of the script is swallowed -- and the exit code is still 0,
    # which is exactly why this went unnoticed in a script using `set -uo pipefail`.
    assert "BEFORE" in eaten.stdout
    assert "AFTER" not in eaten.stdout, "expected the stdin reader to eat the rest of the script"
    assert eaten.returncode == 0, "the silent part: truncation does NOT fail the script"

    fixed = run(
        """
        echo BEFORE
        cat > /dev/null </dev/null
        echo AFTER
        """
    )
    assert "BEFORE" in fixed.stdout and "AFTER" in fixed.stdout


@_needs_checkout
def test_remote_block_is_detected():
    """Guard the guard: if the parser finds nothing, the check below is a no-op."""
    text = open(_SCRIPT, encoding="utf-8").read()
    blocks = _remote_blocks(text)
    assert blocks, (
        "found no `ssh ... 'bash -s' <<'TAG'` block in sync-content.sh -- either "
        "the remote step was removed, or this parser needs updating. It must not "
        "silently pass."
    )


@_needs_checkout
def test_remote_block_is_valid_bash():
    r"""The block must PARSE. This is the check that caught the worse bug.

    The `bash -s` payload is never syntax-checked by anything that runs it: the
    outer script's own `bash -n` passes, because inside a quoted heredoc the
    body is just text. So a broken line sits there looking fine.

    As shipped, the password line read:

        tr -d "\"'"'"'"

    which parses as `"'` + `"` + an UNTERMINATED quote. Remote bash died with
    `unexpected EOF while looking for matching \`"'` before running a single
    command, so the step failed on every run for a reason entirely separate
    from the stdin bug below. Two independent faults, one silent symptom.
    """
    text = open(_SCRIPT, encoding="utf-8").read()
    for tag, body in _remote_blocks(text):
        proc = subprocess.run(
            ["bash", "-n"],
            input=body + "\n",
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert proc.returncode == 0, (
            f"the <<{tag}>> payload is not valid bash, so the remote shell will "
            f"fail before executing anything:\n{proc.stderr.strip()}"
        )


@_needs_checkout
def test_no_unredirected_stdin_reader_in_a_remote_block():
    """The actual regression guard."""
    text = open(_SCRIPT, encoding="utf-8").read()
    offenders = []
    for tag, body in _remote_blocks(text):
        for lineno, line in enumerate(body.splitlines(), start=1):
            code = line.split("#", 1)[0]
            if not code.strip():
                continue
            if _STDIN_READERS.search(code) and not _REDIRECTS_STDIN.search(code):
                offenders.append(f"<<{tag}>> line {lineno}: {line.strip()}")

    assert not offenders, (
        "these commands read stdin inside a `bash -s` payload, so each one "
        "consumes the rest of the remote script and the step silently stops "
        "(exit 0). Add `</dev/null`:\n  " + "\n  ".join(offenders)
    )


@pytest.mark.parametrize(
    "snippet,should_flag",
    [
        ('"${DC[@]}" exec -T redis redis-cli PING', True),
        ('"${DC[@]}" exec -T redis redis-cli PING </dev/null', False),
        ("docker compose exec -T redis redis-cli DBSIZE", True),
        ("docker compose exec -T redis redis-cli DBSIZE < /dev/null", False),
        ("echo hello", False),
        ("PW=$(grep -m1 REDIS_PASSWORD .env.demo)", False),
    ],
)
def test_the_detector_discriminates(snippet, should_flag):
    """Mutation check: the rule must fire on the bug and stay quiet otherwise.

    Without this, a regex that never matched would pass every assertion above.
    """
    flagged = bool(_STDIN_READERS.search(snippet)) and not _REDIRECTS_STDIN.search(snippet)
    assert flagged is should_flag, snippet
