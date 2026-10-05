"""
seed_dev_g8_12.py — Seed G8-12 teachers, students, classrooms for Dev School.

5 teachers (one per grade), 15 students (3 per grade), 5 classrooms with
default curricula linked. Idempotent — safe to re-run.

Usage:
    DATABASE_URL=... python scripts/seed_dev_g8_12.py
"""
from __future__ import annotations

import asyncio
import os

import asyncpg
import bcrypt

DB_URL = os.environ.get("DATABASE_URL", "postgresql://studybuddy:studybuddy@localhost:5432/studybuddy")
SCHOOL_ID = "00000000-0000-0000-0000-000000000001"
TEACHER_PW = "Teacher2026!"
STUDENT_PW = "Student2026!"

TEACHERS = [
    {"id": "e0000000-0000-0000-0000-000000000081", "grade": 8,  "name": "Marcus Rivera",   "email": "marcus.rivera@devschool.dev"},
    {"id": "e0000000-0000-0000-0000-000000000091", "grade": 9,  "name": "Jasmine Patel",   "email": "jasmine.patel@devschool.dev"},
    {"id": "e0000000-0000-0000-0000-000000000101", "grade": 10, "name": "David Kim",        "email": "david.kim@devschool.dev"},
    {"id": "e0000000-0000-0000-0000-000000000111", "grade": 11, "name": "Sophia Garcia",   "email": "sophia.garcia@devschool.dev"},
    {"id": "e0000000-0000-0000-0000-000000000121", "grade": 12, "name": "James Thompson",  "email": "james.thompson@devschool.dev"},
]

STUDENTS = [
    {"id": "f0000000-0000-0000-0000-000000000801", "grade": 8,  "name": "Alex Johnson",    "email": "alex.johnson@devschool.dev"},
    {"id": "f0000000-0000-0000-0000-000000000802", "grade": 8,  "name": "Bailey Smith",    "email": "bailey.smith@devschool.dev"},
    {"id": "f0000000-0000-0000-0000-000000000803", "grade": 8,  "name": "Casey Williams",  "email": "casey.williams@devschool.dev"},
    {"id": "f0000000-0000-0000-0000-000000000901", "grade": 9,  "name": "Dakota Brown",    "email": "dakota.brown@devschool.dev"},
    {"id": "f0000000-0000-0000-0000-000000000902", "grade": 9,  "name": "Era Jones",       "email": "era.jones@devschool.dev"},
    {"id": "f0000000-0000-0000-0000-000000000903", "grade": 9,  "name": "Finley Miller",   "email": "finley.miller@devschool.dev"},
    {"id": "f0000000-0000-0000-0001-000000001001", "grade": 10, "name": "Greyson Davis",   "email": "greyson.davis@devschool.dev"},
    {"id": "f0000000-0000-0000-0001-000000001002", "grade": 10, "name": "Harper Anderson", "email": "harper.anderson@devschool.dev"},
    {"id": "f0000000-0000-0000-0001-000000001003", "grade": 10, "name": "Indigo Taylor",   "email": "indigo.taylor@devschool.dev"},
    {"id": "f0000000-0000-0000-0001-000000001101", "grade": 11, "name": "Jordan Moore",    "email": "jordan.moore@devschool.dev"},
    {"id": "f0000000-0000-0000-0001-000000001102", "grade": 11, "name": "Kendall Jackson", "email": "kendall.jackson@devschool.dev"},
    {"id": "f0000000-0000-0000-0001-000000001103", "grade": 11, "name": "Leslie White",    "email": "leslie.white@devschool.dev"},
    {"id": "f0000000-0000-0000-0001-000000001201", "grade": 12, "name": "Morgan Harris",   "email": "morgan.harris@devschool.dev"},
    {"id": "f0000000-0000-0000-0001-000000001202", "grade": 12, "name": "Noah Martin",     "email": "noah.martin@devschool.dev"},
    {"id": "f0000000-0000-0000-0001-000000001203", "grade": 12, "name": "Oakley Lee",      "email": "oakley.lee@devschool.dev"},
]

CLASSROOMS = [
    {"id": "c0000000-0000-0000-0000-000000000008", "grade": 8,  "name": "Grade 8 Class"},
    {"id": "c0000000-0000-0000-0000-000000000009", "grade": 9,  "name": "Grade 9 Class"},
    {"id": "c0000000-0000-0000-0000-000000000010", "grade": 10, "name": "Grade 10 Class"},
    {"id": "c0000000-0000-0000-0000-000000000011", "grade": 11, "name": "Grade 11 Class"},
    {"id": "c0000000-0000-0000-0000-000000000012", "grade": 12, "name": "Grade 12 Class"},
]

def _hash(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt(12)).decode()

async def main() -> None:
    conn = await asyncpg.connect(DB_URL)
    await conn.execute("SET app.current_school_id = 'bypass'")

    t_hash = _hash(TEACHER_PW)
    s_hash = _hash(STUDENT_PW)

    print("── Teachers ──")
    for t in TEACHERS:
        r = await conn.execute("""
            INSERT INTO teachers (teacher_id, school_id, external_auth_id, auth_provider,
                                  name, email, role, account_status, password_hash, first_login)
            VALUES ($1,$2,$3,'local',$4,$5,'teacher','active',$6,false)
            ON CONFLICT (email) DO NOTHING
        """, t["id"], SCHOOL_ID, f"local:{t['email']}", t["name"], t["email"], t_hash)
        status = "created" if r == "INSERT 0 1" else "exists"
        print(f"  {status}  G{t['grade']}  {t['email']}")

    print("── Students ──")
    for s in STUDENTS:
        r = await conn.execute("""
            INSERT INTO students (student_id, school_id, external_auth_id, auth_provider,
                                  name, email, grade, account_status, password_hash, first_login, enrolled_at)
            VALUES ($1,$2,$3,'local',$4,$5,$6,'active',$7,false,now())
            ON CONFLICT (email) DO NOTHING
        """, s["id"], SCHOOL_ID, f"local:{s['email']}", s["name"], s["email"], s["grade"], s_hash)
        status = "created" if r == "INSERT 0 1" else "exists"
        print(f"  {status}  G{s['grade']}  {s['email']}")

    print("── Classrooms ──")
    teacher_by_grade = {t["grade"]: t["id"] for t in TEACHERS}
    for c in CLASSROOMS:
        r = await conn.execute("""
            INSERT INTO classrooms (classroom_id, school_id, teacher_id, name, grade, status)
            VALUES ($1,$2,$3,$4,$5,'active')
            ON CONFLICT (classroom_id) DO NOTHING
        """, c["id"], SCHOOL_ID, teacher_by_grade[c["grade"]], c["name"], c["grade"])
        status = "created" if r == "INSERT 0 1" else "exists"
        print(f"  {status}  {c['name']}")

    print("── Enroll students ──")
    classroom_by_grade = {c["grade"]: c["id"] for c in CLASSROOMS}
    for s in STUDENTS:
        cid = classroom_by_grade[s["grade"]]
        r = await conn.execute("""
            INSERT INTO classroom_students (classroom_id, student_id)
            VALUES ($1,$2) ON CONFLICT DO NOTHING
        """, cid, s["id"])
        if r == "INSERT 0 1":
            print(f"  enrolled  {s['name']} → G{s['grade']} class")

    print("── Curriculum packages ──")
    for c in CLASSROOMS:
        curriculum_id = f"default-2026-g{c['grade']}"
        r = await conn.execute("""
            INSERT INTO classroom_packages (classroom_id, curriculum_id, sort_order)
            VALUES ($1,$2,0) ON CONFLICT DO NOTHING
        """, c["id"], curriculum_id)
        status = "linked" if r == "INSERT 0 1" else "exists"
        print(f"  {status}  {c['name']} → {curriculum_id}")

    await conn.close()
    print("\nDone.")
    print(f"  Teacher password : {TEACHER_PW}")
    print(f"  Student password : {STUDENT_PW}")

asyncio.run(main())
