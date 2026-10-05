"""
seed_vaganam.py — Seed Vaganam Academy local dev school.

Creates: school, school admin, 2 teachers, 5 students per grade G8-12,
5 classrooms, and default curriculum packages. Idempotent — safe to re-run.

Usage:
    docker compose exec api python scripts/seed_vaganam.py
    # or directly:
    DATABASE_URL=... python scripts/seed_vaganam.py
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncpg
import bcrypt

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://studybuddy:studybuddy_dev@localhost:5432/studybuddy",
)

SCHOOL = {
    "school_id": "a0000000-0000-0000-0000-000000000001",
    "name": "Vaganam Academy",
    "country": "CA",
    "contact_email": "siva.mambakkam@gmail.com",
}

# School admin + teachers share this prefix
SCHOOL_ADMIN = {
    "teacher_id": "a0000000-0000-0000-0000-000000000010",
    "name": "Siva M",
    "email": "siva.mambakkam@gmail.com",
    "role": "school_admin",
}

TEACHERS = [
    {"teacher_id": "a0000000-0000-0000-0000-000000000011", "name": "Ravi Shankar",   "email": "ravi.shankar@vaganam.dev",   "role": "teacher"},
    {"teacher_id": "a0000000-0000-0000-0000-000000000012", "name": "Priya Nair",     "email": "priya.nair@vaganam.dev",     "role": "teacher"},
    {"teacher_id": "a0000000-0000-0000-0000-000000000013", "name": "Arjun Menon",    "email": "arjun.menon@vaganam.dev",    "role": "teacher"},
    {"teacher_id": "a0000000-0000-0000-0000-000000000014", "name": "Deepa Krishnan", "email": "deepa.krishnan@vaganam.dev", "role": "teacher"},
    {"teacher_id": "a0000000-0000-0000-0000-000000000015", "name": "Suresh Iyer",    "email": "suresh.iyer@vaganam.dev",    "role": "teacher"},
]

STUDENTS = [
    # Grade 8
    {"student_id": "a0000000-0000-0000-0008-000000000801", "grade": 8,  "name": "Ananya Kumar",    "email": "ananya.kumar@vaganam.dev"},
    {"student_id": "a0000000-0000-0000-0008-000000000802", "grade": 8,  "name": "Karthik Raj",     "email": "karthik.raj@vaganam.dev"},
    {"student_id": "a0000000-0000-0000-0008-000000000803", "grade": 8,  "name": "Divya Pillai",    "email": "divya.pillai@vaganam.dev"},
    {"student_id": "a0000000-0000-0000-0008-000000000804", "grade": 8,  "name": "Rohan Varma",     "email": "rohan.varma@vaganam.dev"},
    {"student_id": "a0000000-0000-0000-0008-000000000805", "grade": 8,  "name": "Sneha Suresh",    "email": "sneha.suresh@vaganam.dev"},
    # Grade 9
    {"student_id": "a0000000-0000-0000-0009-000000000901", "grade": 9,  "name": "Arun Nambiar",    "email": "arun.nambiar@vaganam.dev"},
    {"student_id": "a0000000-0000-0000-0009-000000000902", "grade": 9,  "name": "Meera Gopalan",   "email": "meera.gopalan@vaganam.dev"},
    {"student_id": "a0000000-0000-0000-0009-000000000903", "grade": 9,  "name": "Vijay Chandran",  "email": "vijay.chandran@vaganam.dev"},
    {"student_id": "a0000000-0000-0000-0009-000000000904", "grade": 9,  "name": "Lakshmi Das",     "email": "lakshmi.das@vaganam.dev"},
    {"student_id": "a0000000-0000-0000-0009-000000000905", "grade": 9,  "name": "Rahul Menon",     "email": "rahul.menon@vaganam.dev"},
    # Grade 10
    {"student_id": "a0000000-0000-0000-0010-000000001001", "grade": 10, "name": "Kavya Nair",      "email": "kavya.nair@vaganam.dev"},
    {"student_id": "a0000000-0000-0000-0010-000000001002", "grade": 10, "name": "Siddharth Rao",   "email": "siddharth.rao@vaganam.dev"},
    {"student_id": "a0000000-0000-0000-0010-000000001003", "grade": 10, "name": "Asha Krishnan",   "email": "asha.krishnan@vaganam.dev"},
    {"student_id": "a0000000-0000-0000-0010-000000001004", "grade": 10, "name": "Nikhil Pillai",   "email": "nikhil.pillai@vaganam.dev"},
    {"student_id": "a0000000-0000-0000-0010-000000001005", "grade": 10, "name": "Preethi Iyer",    "email": "preethi.iyer@vaganam.dev"},
    # Grade 11
    {"student_id": "a0000000-0000-0000-0011-000000001101", "grade": 11, "name": "Arvind Suresh",   "email": "arvind.suresh@vaganam.dev"},
    {"student_id": "a0000000-0000-0000-0011-000000001102", "grade": 11, "name": "Parvathi Nair",   "email": "parvathi.nair@vaganam.dev"},
    {"student_id": "a0000000-0000-0000-0011-000000001103", "grade": 11, "name": "Gopal Menon",     "email": "gopal.menon@vaganam.dev"},
    {"student_id": "a0000000-0000-0000-0011-000000001104", "grade": 11, "name": "Sowmya Raj",      "email": "sowmya.raj@vaganam.dev"},
    {"student_id": "a0000000-0000-0000-0011-000000001105", "grade": 11, "name": "Harish Kumar",    "email": "harish.kumar@vaganam.dev"},
    # Grade 12
    {"student_id": "a0000000-0000-0000-0012-000000001201", "grade": 12, "name": "Revathi Pillai",  "email": "revathi.pillai@vaganam.dev"},
    {"student_id": "a0000000-0000-0000-0012-000000001202", "grade": 12, "name": "Manoj Chandran",  "email": "manoj.chandran@vaganam.dev"},
    {"student_id": "a0000000-0000-0000-0012-000000001203", "grade": 12, "name": "Geetha Varma",    "email": "geetha.varma@vaganam.dev"},
    {"student_id": "a0000000-0000-0000-0012-000000001204", "grade": 12, "name": "Sunil Gopalan",   "email": "sunil.gopalan@vaganam.dev"},
    {"student_id": "a0000000-0000-0000-0012-000000001205", "grade": 12, "name": "Nithya Iyer",     "email": "nithya.iyer@vaganam.dev"},
]

CLASSROOMS = [
    {"classroom_id": "a0000000-0000-0000-0000-000000000008", "grade": 8,  "name": "Grade 8 — Vaganam"},
    {"classroom_id": "a0000000-0000-0000-0000-000000000009", "grade": 9,  "name": "Grade 9 — Vaganam"},
    {"classroom_id": "a0000000-0000-0000-0000-000000000010", "grade": 10, "name": "Grade 10 — Vaganam"},
    {"classroom_id": "a0000000-0000-0000-0000-000000000011", "grade": 11, "name": "Grade 11 — Vaganam"},
    {"classroom_id": "a0000000-0000-0000-0000-000000000012", "grade": 12, "name": "Grade 12 — Vaganam"},
]

PASSWORD = "vaganam@2026"


def _hash(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt(12)).decode()


async def main() -> None:
    conn = await asyncpg.connect(DB_URL)
    await conn.execute("SET app.current_school_id = 'bypass'")

    pw_hash = _hash(PASSWORD)

    # ── School ────────────────────────────────────────────────────────────────
    existing = await conn.fetchrow(
        "SELECT school_id FROM schools WHERE school_id = $1", SCHOOL["school_id"]
    )
    if existing:
        print(f"  school exists — {SCHOOL['name']}")
    else:
        await conn.execute(
            "INSERT INTO schools (school_id, name, country, contact_email, status) "
            "VALUES ($1,$2,$3,$4,'active')",
            SCHOOL["school_id"], SCHOOL["name"], SCHOOL["country"], SCHOOL["contact_email"],
        )
        print(f"  created school — {SCHOOL['name']}")

    # ── School admin + teachers ───────────────────────────────────────────────
    print("── Teachers ──")
    all_teachers = [SCHOOL_ADMIN] + TEACHERS
    teacher_by_grade = {8: TEACHERS[0]["teacher_id"], 9: TEACHERS[1]["teacher_id"],
                        10: TEACHERS[2]["teacher_id"], 11: TEACHERS[3]["teacher_id"],
                        12: TEACHERS[4]["teacher_id"]}

    for t in all_teachers:
        r = await conn.execute(
            "INSERT INTO teachers "
            "(teacher_id, school_id, name, email, role, auth_provider, external_auth_id, "
            " password_hash, first_login, account_status) "
            "VALUES ($1,$2,$3,$4,$5,'local',$6,$7,false,'active') "
            "ON CONFLICT (email) DO NOTHING",
            t["teacher_id"], SCHOOL["school_id"], t["name"], t["email"],
            t["role"], f"local:{t['email']}", pw_hash,
        )
        status = "created" if r == "INSERT 0 1" else "exists "
        print(f"  {status}  [{t['role']:<12}]  {t['email']}")

    # ── Students ──────────────────────────────────────────────────────────────
    print("── Students ──")
    for s in STUDENTS:
        r = await conn.execute(
            "INSERT INTO students "
            "(student_id, school_id, name, email, grade, auth_provider, external_auth_id, "
            " password_hash, first_login, account_status, enrolled_at) "
            "VALUES ($1,$2,$3,$4,$5,'local',$6,$7,false,'active',now()) "
            "ON CONFLICT (email) DO NOTHING",
            s["student_id"], SCHOOL["school_id"], s["name"], s["email"],
            s["grade"], f"local:{s['email']}", pw_hash,
        )
        status = "created" if r == "INSERT 0 1" else "exists "
        print(f"  {status}  G{s['grade']}  {s['email']}")

    # ── Classrooms ────────────────────────────────────────────────────────────
    print("── Classrooms ──")
    for c in CLASSROOMS:
        r = await conn.execute(
            "INSERT INTO classrooms (classroom_id, school_id, teacher_id, name, grade, status) "
            "VALUES ($1,$2,$3,$4,$5,'active') ON CONFLICT (classroom_id) DO NOTHING",
            c["classroom_id"], SCHOOL["school_id"],
            teacher_by_grade[c["grade"]], c["name"], c["grade"],
        )
        status = "created" if r == "INSERT 0 1" else "exists "
        print(f"  {status}  {c['name']}")

    # ── Enroll students ───────────────────────────────────────────────────────
    classroom_by_grade = {c["grade"]: c["classroom_id"] for c in CLASSROOMS}
    for s in STUDENTS:
        await conn.execute(
            "INSERT INTO classroom_students (classroom_id, student_id) "
            "VALUES ($1,$2) ON CONFLICT DO NOTHING",
            classroom_by_grade[s["grade"]], s["student_id"],
        )

    # ── Curriculum packages ───────────────────────────────────────────────────
    print("── Curriculum packages ──")
    for c in CLASSROOMS:
        curriculum_id = f"default-2026-g{c['grade']}"
        r = await conn.execute(
            "INSERT INTO classroom_packages (classroom_id, curriculum_id, sort_order) "
            "VALUES ($1,$2,0) ON CONFLICT DO NOTHING",
            c["classroom_id"], curriculum_id,
        )
        status = "linked" if r == "INSERT 0 1" else "exists"
        print(f"  {status}  {c['name']} → {curriculum_id}")

    # ── School subscription ───────────────────────────────────────────────────
    existing_sub = await conn.fetchrow(
        "SELECT school_subscription_id FROM school_subscriptions WHERE school_id = $1", SCHOOL["school_id"]
    )
    if not existing_sub:
        await conn.execute(
            "INSERT INTO school_subscriptions "
            "(school_id, plan, status, stripe_customer_id, stripe_subscription_id, "
            " current_period_end) "
            "VALUES ($1,'enterprise','active','dev_cus_vaganam','dev_sub_vaganam',"
            " now() + interval '365 days')",
            SCHOOL["school_id"],
        )
        print("  created school subscription (1 year)")
    else:
        print("  subscription exists")

    await conn.close()

    print()
    print("─" * 55)
    print("  Vaganam Academy seeded")
    print("─" * 55)
    print(f"  All passwords : {PASSWORD}")
    print(f"  School admin  : {SCHOOL_ADMIN['email']}")
    print("  Teachers      : ravi.shankar@ … suresh.iyer@vaganam.dev")
    print("  Students      : 5 per grade, G8-12 (25 total)")
    print()


asyncio.run(main())
