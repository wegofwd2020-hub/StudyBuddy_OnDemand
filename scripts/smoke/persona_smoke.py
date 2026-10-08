#!/usr/bin/env python3
"""
scripts/smoke/persona_smoke.py — on-demand persona smoke test harness

Creates its own test fixtures via the API, runs persona checks for super-admin,
teacher, and student (G9–G12), then deletes every fixture it created.

Usage:
  # Local dev (./dev_start.sh must be running):
  python scripts/smoke/persona_smoke.py \\
      --url http://127.0.0.1:8001 \\
      --admin-email admin@example.com \\
      --admin-password "Password123!"

  # Against the live demo:
  python scripts/smoke/persona_smoke.py \\
      --url https://demo.usestudybuddy.com \\
      --admin-email admin@example.com \\
      --admin-password "Password123!"

  # Keep fixtures after the run (useful when investigating a failure):
  python scripts/smoke/persona_smoke.py --url ... --no-teardown

Exit codes:
  0  all checks passed
  1  one or more checks failed (teardown still ran unless --no-teardown)
  2  setup or teardown error

Fixtures created (all deleted on teardown via DELETE /admin/test-schools/{id}):
  - 1 school:   "smoketest-{run_id}" (school_admin = the registering user)
  - 1 teacher:  smoke-teacher-{run_id}@smoke.example.com  (grades 9–12 assigned)
  - 4 students: smoke-g{N}-{run_id}@smoke.example.com for N in 9, 10, 11, 12
  - 4 classrooms, 1 per grade, each with a catalog curriculum package
  - 4 classroom-student assignments (1 student per classroom)

Reports written to reports/smoke/ (gitignored — never committed):
  {timestamp}-{env}.json   machine-readable result
  {timestamp}-{env}.md     human-readable Markdown
  latest-{env}.json        always overwritten — quick access
  latest-{env}.md

Requires:  pip install requests
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime
import json
import pathlib
import sys
import time
from itertools import groupby
from typing import Any
from urllib.parse import urlparse

try:
    import requests as _requests
except ImportError:
    print("requests not installed.  Run: pip install requests", file=sys.stderr)
    sys.exit(2)

# ── Config ────────────────────────────────────────────────────────────────────
GRADES = [9, 10, 11, 12]
# Password used for all provisioned accounts after the forced reset.
# Must be 12+ chars (backend validator).
STABLE_PASSWORD = "SmokeTest@2026!"

# ── Colour helpers ────────────────────────────────────────────────────────────
GREEN  = "\033[0;32m"
RED    = "\033[0;31m"
YELLOW = "\033[0;33m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

_failures: list[str] = []
_warnings: list[str] = []


# ── Report collector ──────────────────────────────────────────────────────────
@dataclasses.dataclass
class _Check:
    section: str
    label: str
    status: str   # "pass" | "fail" | "warn"
    detail: str


def _env_label(url: str) -> str:
    if "127.0.0.1" in url or "localhost" in url:
        return "local"
    host = urlparse(url).hostname or url
    return host.split(".")[0]


def _render_md(data: dict) -> str:
    s = data["summary"]
    overall = "❌" if s["fail"] else "✅"
    warn_part = f"⚠️ {s['warn']} warning(s)" if s["warn"] else f"— {s['warn']} warnings"
    fail_part = f"❌ {s['fail']} failed" if s["fail"] else f"— {s['fail']} failed"

    lines = [
        "# StudyBuddy Smoke Test Report",
        "",
        f"**Target:** {data['target']}  ",
        f"**Env:** {data['env']}  ",
        f"**Run ID:** {data['run_id']}  ",
        f"**Date:** {data['timestamp']}  ",
        f"**Duration:** {data['duration_s']}s  ",
        "",
        "## Summary",
        "",
        f"{overall} **{s['pass']} passed** · {warn_part} · {fail_part}",
        "",
    ]

    if not data["setup_ok"]:
        lines += ["> ⚠️ Setup did not complete — checks below may be incomplete.", ""]
    if not data["teardown_ok"]:
        lines += ["> ⚠️ Teardown failed — test fixtures may remain in the database.", ""]

    lines += ["## Checks", ""]
    for section_name, checks in groupby(data["checks"], key=lambda c: c["section"]):
        lines.append(f"### {section_name}")
        lines.append("")
        lines.append("| Status | Check | Detail |")
        lines.append("|---|---|---|")
        for c in checks:
            icon = {"pass": "✅", "fail": "❌", "warn": "⚠️"}.get(c["status"], "?")
            detail = (c["detail"] or "—").replace("|", "\\|")
            lines.append(f"| {icon} | {c['label']} | {detail} |")
        lines.append("")

    return "\n".join(lines)


class Reporter:
    def __init__(self) -> None:
        self._section = ""
        self._checks: list[_Check] = []
        self._start: float = time.time()

    def set_section(self, title: str) -> None:
        self._section = title

    def record(self, status: str, label: str, detail: str = "") -> None:
        self._checks.append(_Check(self._section, label, status, detail))

    def write(
        self,
        base_url: str,
        run_id: str,
        *,
        setup_ok: bool,
        teardown_ok: bool,
    ) -> None:
        duration = round(time.time() - self._start, 1)
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        env = _env_label(base_url)
        stamp = now.strftime("%Y-%m-%dT%H-%M-%S")

        report_dir = pathlib.Path(__file__).parent.parent.parent / "reports" / "smoke"
        report_dir.mkdir(parents=True, exist_ok=True)

        data: dict[str, Any] = {
            "run_id": run_id,
            "env": env,
            "target": base_url,
            "timestamp": now.isoformat(),
            "duration_s": duration,
            "setup_ok": setup_ok,
            "teardown_ok": teardown_ok,
            "summary": {
                "pass": sum(1 for c in self._checks if c.status == "pass"),
                "warn": sum(1 for c in self._checks if c.status == "warn"),
                "fail": sum(1 for c in self._checks if c.status == "fail"),
            },
            "checks": [dataclasses.asdict(c) for c in self._checks],
        }

        json_body = json.dumps(data, indent=2)
        (report_dir / f"{stamp}-{env}.json").write_text(json_body)
        (report_dir / f"latest-{env}.json").write_text(json_body)

        md_body = _render_md(data)
        (report_dir / f"{stamp}-{env}.md").write_text(md_body)
        (report_dir / f"latest-{env}.md").write_text(md_body)

        print(f"\n  {BOLD}Report:{RESET} reports/smoke/{stamp}-{env}.md")


# Module-level singleton — reset in main() so the timer starts at invocation.
_reporter = Reporter()


def ok(label: str) -> None:
    print(f"  {GREEN}✓{RESET} {label}")
    _reporter.record("pass", label)


def fail(label: str, detail: str = "") -> None:
    msg = f"{label}{': ' + detail if detail else ''}"
    print(f"  {RED}✗{RESET} {msg}")
    _failures.append(msg)
    _reporter.record("fail", label, detail)


def warn(label: str, detail: str = "") -> None:
    msg = f"{label}{': ' + detail if detail else ''}"
    print(f"  {YELLOW}~{RESET} {msg}")
    _warnings.append(msg)
    _reporter.record("warn", label, detail)


def section(title: str) -> None:
    print(f"\n{BOLD}{title}{RESET}")
    _reporter.set_section(title)


# ── HTTP client ───────────────────────────────────────────────────────────────
_s = _requests.Session()


def _req(
    method: str,
    base: str,
    path: str,
    *,
    token: str | None = None,
    body: Any = None,
    timeout: int = 20,
) -> _requests.Response:
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return _s.request(
        method,
        f"{base.rstrip('/')}{path}",
        json=body,
        headers=headers,
        timeout=timeout,
    )


# ── Auth helpers ──────────────────────────────────────────────────────────────
def admin_login(base: str, email: str, password: str) -> str:
    r = _req("POST", base, "/api/v1/admin/auth/login",
             body={"email": email, "password": password})
    if r.status_code != 200:
        raise RuntimeError(f"admin login failed {r.status_code}: {r.text[:160]}")
    return r.json()["token"]


def _universal_login(base: str, email: str, password: str) -> tuple[str, bool]:
    """Returns (token, first_login)."""
    r = _req("POST", base, "/api/v1/auth/universal-login",
             body={"email": email, "password": password})
    if r.status_code != 200:
        raise RuntimeError(f"login failed for {email} {r.status_code}: {r.text[:160]}")
    d = r.json()
    return d["token"], bool(d.get("first_login"))


def _change_password(base: str, token: str, current_pw: str, new_pw: str) -> str:
    """Clears first_login=True, returns fresh token."""
    r = _req("PATCH", base, "/api/v1/auth/change-password",
             token=token,
             body={"current_password": current_pw, "new_password": new_pw})
    if r.status_code != 200:
        raise RuntimeError(f"change-password failed {r.status_code}: {r.text[:160]}")
    return r.json()["token"]


def _reset_and_get_stable_token(
    base: str,
    school_id: str,
    school_token: str,
    kind: str,
    user_id: str,
    email: str,
) -> str:
    """
    Reset the provisioned account's password (returns temp_password),
    login with it, then change to STABLE_PASSWORD to clear first_login.
    Returns a stable JWT with first_login=False.
    """
    path = f"/api/v1/schools/{school_id}/{kind}s/{user_id}/reset-password"
    r = _req("POST", base, path, token=school_token)
    if r.status_code != 200:
        raise RuntimeError(
            f"reset-password failed for {kind} {user_id}: {r.status_code} {r.text[:160]}"
        )
    temp_pw = r.json()["temp_password"]

    initial_token, first_login = _universal_login(base, email, temp_pw)
    if not first_login:
        return initial_token
    return _change_password(base, initial_token, temp_pw, STABLE_PASSWORD)


# ── Setup ─────────────────────────────────────────────────────────────────────
def setup(base: str, run_id: str) -> dict:
    """
    Create school + teacher (with grades) + students + classrooms + packages.
    Returns the fixture state dict used by tests and teardown.
    """
    state: dict[str, Any] = {
        "school_id": None,
        "school_admin_token": None,
        "teacher_id": None,
        "teacher_token": None,
        "students": {},    # grade → {id, email, token}
        "classrooms": {},  # grade → classroom_id
    }

    # 1. Register school — first_login=False, returns access_token directly
    section("Setup — school registration")
    admin_email = f"smokeadmin-{run_id}@smoke.example.com"
    r = _req("POST", base, "/api/v1/schools/register", body={
        "school_name": f"smoketest-{run_id}",
        "contact_email": admin_email,
        "country": "CA",
        "password": STABLE_PASSWORD,
    })
    if r.status_code != 201:
        raise RuntimeError(f"register failed {r.status_code}: {r.text[:200]}")
    reg = r.json()
    state["school_id"] = reg["school_id"]
    # Use the returned token directly (register sets first_login=False)
    state["school_admin_token"] = reg["access_token"]
    print(f"  school_id={reg['school_id']}")

    school_id = state["school_id"]
    school_token = state["school_admin_token"]

    # 2. Provision teacher
    section("Setup — teacher")
    teacher_email = f"smoke-teacher-{run_id}@smoke.example.com"
    r = _req("POST", base, f"/api/v1/schools/{school_id}/teachers",
             token=school_token,
             body={"name": "Smoke Teacher", "email": teacher_email})
    if r.status_code != 201:
        raise RuntimeError(f"provision teacher failed {r.status_code}: {r.text[:200]}")
    teacher_id = r.json()["teacher_id"]
    state["teacher_id"] = teacher_id
    print(f"  teacher_id={teacher_id}")

    # Assign grades 9–12 so grade_filter returns a non-empty set
    r = _req("PUT", base, f"/api/v1/schools/{school_id}/teachers/{teacher_id}/grades",
             token=school_token,
             body={"grades": GRADES})
    if r.status_code != 200:
        raise RuntimeError(
            f"teacher grade assign failed {r.status_code}: {r.text[:200]}"
        )
    print(f"  grades assigned: {GRADES}")

    teacher_token = _reset_and_get_stable_token(
        base, school_id, school_token, "teacher", teacher_id, teacher_email
    )
    state["teacher_token"] = teacher_token
    print(f"  teacher login OK")

    # 3. Provision students for each grade
    section("Setup — students (G9–G12)")
    for grade in GRADES:
        email = f"smoke-g{grade}-{run_id}@smoke.example.com"
        r = _req("POST", base, f"/api/v1/schools/{school_id}/students",
                 token=school_token,
                 body={"name": f"Smoke Student G{grade}", "email": email, "grade": grade})
        if r.status_code != 201:
            raise RuntimeError(
                f"provision student G{grade} failed {r.status_code}: {r.text[:200]}"
            )
        sid = r.json()["student_id"]
        token = _reset_and_get_stable_token(
            base, school_id, school_token, "student", sid, email
        )
        state["students"][grade] = {"id": sid, "email": email, "token": token}
        print(f"  G{grade}: student_id={sid} login OK")

    # 4. Discover curriculum packages per grade from the catalog
    section("Setup — curriculum catalog")
    r = _req("GET", base, "/api/v1/curricula/catalog", token=school_token)
    if r.status_code != 200:
        raise RuntimeError(f"catalog fetch failed {r.status_code}: {r.text[:120]}")
    catalog_by_grade: dict[int, str] = {}
    for pkg in r.json().get("packages", []):
        g = pkg.get("grade")
        if g in GRADES and g not in catalog_by_grade:
            catalog_by_grade[g] = pkg["curriculum_id"]
    found = sorted(catalog_by_grade.keys())
    print(f"  packages found for grades: {found}")
    missing = [g for g in GRADES if g not in catalog_by_grade]
    if missing:
        warn("catalog", f"no package for grade(s) {missing} — lesson checks will be skipped")

    # 5. Create classrooms, assign packages + students
    section("Setup — classrooms")
    for grade in GRADES:
        r = _req("POST", base, f"/api/v1/schools/{school_id}/classrooms",
                 token=school_token,
                 body={"name": f"Smoke G{grade}", "grade": grade, "teacher_id": teacher_id})
        if r.status_code != 201:
            raise RuntimeError(
                f"create classroom G{grade} failed {r.status_code}: {r.text[:200]}"
            )
        cid = r.json()["classroom_id"]
        state["classrooms"][grade] = cid

        if grade in catalog_by_grade:
            r2 = _req("POST", base,
                      f"/api/v1/schools/{school_id}/classrooms/{cid}/packages",
                      token=school_token,
                      body={"curriculum_id": catalog_by_grade[grade]})
            if r2.status_code not in (200, 201, 204):
                warn(f"assign package G{grade}", f"status={r2.status_code}")

        sid = state["students"][grade]["id"]
        r3 = _req("POST", base,
                  f"/api/v1/schools/{school_id}/classrooms/{cid}/students",
                  token=school_token,
                  body={"student_id": sid})
        if r3.status_code not in (200, 201, 204):
            warn(f"assign student G{grade}", f"status={r3.status_code}")

        print(f"  G{grade}: classroom_id={cid}")

    print(f"\n  {GREEN}Setup complete — run_id={run_id}{RESET}")
    return state


# ── Persona tests ─────────────────────────────────────────────────────────────
def test_super_admin(base: str, admin_token: str) -> None:
    section("Persona: super-admin")

    r = _req("GET", base, "/api/v1/admin/audit?limit=5", token=admin_token)
    if r.status_code == 200:
        ok("GET /admin/audit → 200")
    else:
        fail("GET /admin/audit", f"status={r.status_code}")

    r = _req("GET", base, "/api/v1/admin/pipeline/jobs?limit=5", token=admin_token)
    if r.status_code == 200:
        ok("GET /admin/pipeline/jobs → 200")
    else:
        fail("GET /admin/pipeline/jobs", f"status={r.status_code}")

    r = _req("GET", base, "/api/v1/admin/pipeline/status", token=admin_token)
    if r.status_code == 200:
        ok("GET /admin/pipeline/status → 200")
    else:
        fail("GET /admin/pipeline/status", f"status={r.status_code}")

    r = _req("GET", base, "/api/v1/admin/content/review/queue?limit=5", token=admin_token)
    if r.status_code == 200:
        ok("GET /admin/content/review/queue → 200")
    else:
        fail("GET /admin/content/review/queue", f"status={r.status_code}")

    r = _req("GET", base, "/api/v1/admin/users", token=admin_token)
    if r.status_code == 200:
        ok("GET /admin/users → 200")
    else:
        fail("GET /admin/users", f"status={r.status_code}")


def test_teacher(
    base: str,
    teacher_token: str,
    school_id: str,
    classrooms: dict[int, str],
) -> None:
    section("Persona: teacher")

    r = _req("GET", base, "/api/v1/curricula/catalog", token=teacher_token)
    if r.status_code == 200:
        count = len(r.json().get("packages", []))
        ok(f"GET /curricula/catalog → 200 ({count} packages)")
    else:
        fail("GET /curricula/catalog", f"status={r.status_code}")

    r = _req("GET", base, f"/api/v1/schools/{school_id}/classrooms", token=teacher_token)
    if r.status_code == 200:
        count = len(r.json())
        ok(f"GET /schools/{{id}}/classrooms → 200 ({count} classrooms)")
        if count != len(GRADES):
            warn("classroom count", f"expected {len(GRADES)}, got {count}")
    else:
        fail("GET /schools/classrooms", f"status={r.status_code}")

    # Detail check for one classroom
    for grade in GRADES:
        if grade not in classrooms:
            continue
        cid = classrooms[grade]
        r = _req("GET", base, f"/api/v1/schools/{school_id}/classrooms/{cid}",
                 token=teacher_token)
        if r.status_code == 200:
            d = r.json()
            pkg_count = len(d.get("packages", []))
            stu_count = len(d.get("students", []))
            ok(
                f"GET classroom detail G{grade} → 200 "
                f"({pkg_count} package(s), {stu_count} student(s))"
            )
        else:
            fail(f"GET classroom detail G{grade}", f"status={r.status_code}")
        break  # one is enough for the persona check


def test_students(base: str, students: dict[int, dict]) -> None:
    section("Persona: students (G9–G12)")

    for grade, info in students.items():
        token = info["token"]

        # Curriculum tree (stream-aware; returns the school's curriculum when
        # the student is logged in and requests their own grade)
        r = _req("GET", base, f"/api/v1/curriculum/{grade}", token=token)
        if r.status_code != 200:
            fail(f"G{grade} GET /curriculum/{grade}", f"status={r.status_code}")
            continue

        subjects = r.json().get("subjects", [])
        unit_ids = [u["unit_id"] for s in subjects for u in s.get("units", [])]
        ok(f"G{grade}: GET /curriculum/{grade} → 200 ({len(unit_ids)} units)")

        if not unit_ids:
            warn(f"G{grade}: no units in curriculum tree — skipping lesson check")
            continue

        # Lesson fetch: 200 = content built; 404 = not built yet (non-blocking);
        # 402 = entitlement failure (blocking); 5xx = crash (blocking)
        unit_id = unit_ids[0]
        r = _req("GET", base, f"/api/v1/content/{unit_id}/lesson", token=token)
        if r.status_code == 200:
            ok(f"G{grade}: GET /content/{unit_id}/lesson → 200")
        elif r.status_code == 404:
            warn(
                f"G{grade}: GET /content/{unit_id}/lesson → 404",
                "content not yet built for this unit (run the pipeline first)",
            )
        elif r.status_code == 402:
            fail(
                f"G{grade}: GET /content/{unit_id}/lesson",
                "402 — entitlement check failing (missing school subscription?)",
            )
        else:
            fail(
                f"G{grade}: GET /content/{unit_id}/lesson",
                f"unexpected status={r.status_code}",
            )


# ── Teardown ──────────────────────────────────────────────────────────────────
def teardown(base: str, admin_token: str, school_id: str) -> bool:
    """Returns True if teardown succeeded."""
    section("Teardown")
    r = _req("DELETE", base, f"/api/v1/admin/test-schools/{school_id}", token=admin_token)
    if r.status_code == 204:
        ok(f"school {school_id} deleted (cascade)")
        return True
    print(
        f"  {RED}✗{RESET} teardown failed: "
        f"status={r.status_code} {r.text[:120]}"
    )
    print(
        f"\n  Manual cleanup (inside api container):\n"
        f"    psql -c \"DELETE FROM schools "
        f"WHERE school_id = '{school_id}';\""
    )
    return False


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> int:
    global _reporter, _failures, _warnings
    _reporter = Reporter()
    _failures = []
    _warnings = []

    parser = argparse.ArgumentParser(
        description="StudyBuddy on-demand persona smoke test harness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8001",
        help="API base URL (default: http://127.0.0.1:8001)",
    )
    parser.add_argument("--admin-email", required=True, metavar="EMAIL")
    parser.add_argument("--admin-password", required=True, metavar="PASSWORD")
    parser.add_argument(
        "--run-id",
        default=None,
        help="Override run ID suffix (default: Unix timestamp)",
    )
    parser.add_argument(
        "--no-teardown",
        action="store_true",
        help="Skip fixture deletion after the run (useful for debugging failures)",
    )
    args = parser.parse_args()

    run_id = args.run_id or str(int(time.time()))
    base = args.url.rstrip("/")

    print(f"\n{BOLD}=== StudyBuddy persona smoke test ==={RESET}")
    print(f"    target:  {base}")
    print(f"    run_id:  {run_id}")
    print(f"    grades:  {GRADES}")
    if args.no_teardown:
        print(f"    {YELLOW}--no-teardown: fixtures will NOT be deleted{RESET}")

    # Admin login
    section("Admin login")
    try:
        admin_token = admin_login(base, args.admin_email, args.admin_password)
        ok(f"admin login OK ({args.admin_email})")
    except Exception as exc:
        print(f"  {RED}✗{RESET} {exc}")
        _reporter.write(base, run_id, setup_ok=False, teardown_ok=False)
        return 2

    # Setup fixtures
    setup_ok = False
    teardown_ok = False
    state: dict | None = None
    try:
        state = setup(base, run_id)
        setup_ok = True
    except Exception as exc:
        print(f"\n  {RED}✗{RESET} setup failed: {exc}")
        if state and state.get("school_id") and not args.no_teardown:
            teardown_ok = teardown(base, admin_token, state["school_id"])
        _reporter.write(base, run_id, setup_ok=False, teardown_ok=teardown_ok)
        return 2

    # Run persona checks — always teardown afterwards (unless --no-teardown)
    try:
        test_super_admin(base, admin_token)
        test_teacher(base, state["teacher_token"], state["school_id"], state["classrooms"])
        test_students(base, state["students"])
    finally:
        if not args.no_teardown:
            teardown_ok = teardown(base, admin_token, state["school_id"])
        else:
            teardown_ok = True  # skipped by choice — not a failure
            print(
                f"\n  {YELLOW}Fixtures preserved (--no-teardown).{RESET}\n"
                f"  To clean up manually:\n"
                f"    python scripts/smoke/persona_smoke.py --teardown-school {state['school_id']}\n"
                f"  Or inside the api container:\n"
                f"    psql -c \"DELETE FROM schools WHERE school_id = '{state['school_id']}';\""
            )

    # Summary
    print(f"\n{'─' * 44}")
    if _failures:
        print(f"{RED}{BOLD}{len(_failures)} check(s) FAILED:{RESET}")
        for f in _failures:
            print(f"  {RED}•{RESET} {f}")
        if _warnings:
            print(f"\n{YELLOW}{len(_warnings)} warning(s):{RESET}")
            for w in _warnings:
                print(f"  {YELLOW}~{RESET} {w}")
        _reporter.write(base, run_id, setup_ok=setup_ok, teardown_ok=teardown_ok)
        return 1

    print(f"{GREEN}{BOLD}All persona checks passed.{RESET}")
    if _warnings:
        print(f"\n{YELLOW}{len(_warnings)} warning(s) (non-blocking):{RESET}")
        for w in _warnings:
            print(f"  {YELLOW}~{RESET} {w}")

    _reporter.write(base, run_id, setup_ok=setup_ok, teardown_ok=teardown_ok)
    return 0


if __name__ == "__main__":
    sys.exit(main())
