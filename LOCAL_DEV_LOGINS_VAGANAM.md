# StudyBuddy Local Dev — Vaganam Academy Logins

Base URL: **http://localhost:3000**  
School: **Vaganam Academy**  
All passwords: **vaganam@2026**

---

## Super Admin

| Portal | Email | Password |
|--------|-------|----------|
| http://localhost:3000/admin/login | wegofwd2020@gmail.com | vaganam@2026 |

---

## School Admin / Teachers

Login at: **http://localhost:3000/school/login**

| Name | Email | Role | Grade |
|------|-------|------|-------|
| Siva M | siva.mambakkam@gmail.com | school_admin | — |
| Ravi Shankar | ravi.shankar@vaganam.dev | teacher | G8 |
| Priya Nair | priya.nair@vaganam.dev | teacher | G9 |
| Arjun Menon | arjun.menon@vaganam.dev | teacher | G10 |
| Deepa Krishnan | deepa.krishnan@vaganam.dev | teacher | G11 |
| Suresh Iyer | suresh.iyer@vaganam.dev | teacher | G12 |

---

## Students

Login at: **http://localhost:3000/signin**

| Email | Grade | Classroom |
|-------|-------|-----------|
| ananya.kumar@vaganam.dev | 8 | Grade 8 — Vaganam |
| karthik.raj@vaganam.dev | 8 | Grade 8 — Vaganam |
| divya.pillai@vaganam.dev | 8 | Grade 8 — Vaganam |
| rohan.varma@vaganam.dev | 8 | Grade 8 — Vaganam |
| sneha.suresh@vaganam.dev | 8 | Grade 8 — Vaganam |
| arun.nambiar@vaganam.dev | 9 | Grade 9 — Vaganam |
| meera.gopalan@vaganam.dev | 9 | Grade 9 — Vaganam |
| vijay.chandran@vaganam.dev | 9 | Grade 9 — Vaganam |
| lakshmi.das@vaganam.dev | 9 | Grade 9 — Vaganam |
| rahul.menon@vaganam.dev | 9 | Grade 9 — Vaganam |
| kavya.nair@vaganam.dev | 10 | Grade 10 — Vaganam |
| siddharth.rao@vaganam.dev | 10 | Grade 10 — Vaganam |
| asha.krishnan@vaganam.dev | 10 | Grade 10 — Vaganam |
| nikhil.pillai@vaganam.dev | 10 | Grade 10 — Vaganam |
| preethi.iyer@vaganam.dev | 10 | Grade 10 — Vaganam |
| arvind.suresh@vaganam.dev | 11 | Grade 11 — Vaganam |
| parvathi.nair@vaganam.dev | 11 | Grade 11 — Vaganam |
| gopal.menon@vaganam.dev | 11 | Grade 11 — Vaganam |
| sowmya.raj@vaganam.dev | 11 | Grade 11 — Vaganam |
| harish.kumar@vaganam.dev | 11 | Grade 11 — Vaganam |
| revathi.pillai@vaganam.dev | 12 | Grade 12 — Vaganam |
| manoj.chandran@vaganam.dev | 12 | Grade 12 — Vaganam |
| geetha.varma@vaganam.dev | 12 | Grade 12 — Vaganam |
| sunil.gopalan@vaganam.dev | 12 | Grade 12 — Vaganam |
| nithya.iyer@vaganam.dev | 12 | Grade 12 — Vaganam |

---

## Curriculum Packages

| Classroom | Curriculum ID | Content |
|-----------|--------------|---------|
| Grade 8 | default-2026-g8 | build if needed: `python pipeline/build_grade.py --grade 8 --lang en` |
| Grade 9 | default-2026-g9 | build if needed |
| Grade 10 | default-2026-g10 | build if needed |
| Grade 11 | default-2026-g11 | build if needed |
| Grade 12 | default-2026-g12 | build if needed |

---

## Dev Magic Login (no password)

http://localhost:3000/dev-login — pick Student, Teacher, or School Admin instantly.

---

## Stack

```
API      http://127.0.0.1:8001
Web      http://localhost:3000
Admin    http://localhost:3000/admin/login
```

Networking note: after reboot run:
```bash
sudo ip rule add to 172.18.0.0/16 lookup main priority 100
sudo ip rule add to 172.17.0.0/16 lookup main priority 101
```
