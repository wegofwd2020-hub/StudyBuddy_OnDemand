# StudyBuddy Local Dev — Login Credentials

Base URL: **http://localhost:3000**

School: **Vaganam Academy**

---

## Super Admin

| Portal | Email | Password |
|--------|-------|----------|
| http://localhost:3000/admin/login | wegofwd2020@gmail.com | vaganam@2026 |

---

## School Admin / Teacher

Login at: **http://localhost:3000/school/login**

All passwords: **vaganam@2026**

| Name | Email | Role | Classroom |
|------|-------|------|-----------|
| Siva Mambakkam | siva.mambakkam@gmail.com | school_admin | — |
| Ravi Shankar | ravi.shankar@vaganam.dev | teacher | Grade 8 — Vaganam |
| Priya Nair | priya.nair@vaganam.dev | teacher | Grade 9 — Vaganam |
| Arjun Menon | arjun.menon@vaganam.dev | teacher | Grade 10 — Vaganam |
| Deepa Krishnan | deepa.krishnan@vaganam.dev | teacher | Grade 11 — Vaganam + Humanities |
| Suresh Iyer | suresh.iyer@vaganam.dev | teacher | Grade 12 — Vaganam |

---

## Content Status

| Curriculum | Units | Subjects | Status |
|---|---|---|---|
| G8 Science | — | — | ✅ Live |
| G11 Science | 29 | Physics, Chemistry, Math, Biology | ✅ Live |
| G11 Humanities | 9 | History, Geography, Politics, Psychology | ✅ Live |
| G12 Commerce | 7 | Accounting, Business, Economics | ✅ Live |
| G12 Science | 28 | Physics, Chemistry, Math, Biology | ✅ Live |

---

## Students

Login at: **http://localhost:3000/signin**

All passwords: **vaganam@2026**

| Email | Grade | Classroom | Teacher |
|-------|-------|-----------|---------|
| ananya.kumar@vaganam.dev | 8 | Grade 8 — Vaganam | Ravi Shankar |
| divya.pillai@vaganam.dev | 8 | Grade 8 — Vaganam | Ravi Shankar |
| karthik.raj@vaganam.dev | 8 | Grade 8 — Vaganam | Ravi Shankar |
| rohan.varma@vaganam.dev | 8 | Grade 8 — Vaganam | Ravi Shankar |
| sneha.suresh@vaganam.dev | 8 | Grade 8 — Vaganam | Ravi Shankar |
| arun.nambiar@vaganam.dev | 9 | Grade 9 — Vaganam | Priya Nair |
| lakshmi.das@vaganam.dev | 9 | Grade 9 — Vaganam | Priya Nair |
| meera.gopalan@vaganam.dev | 9 | Grade 9 — Vaganam | Priya Nair |
| rahul.menon@vaganam.dev | 9 | Grade 9 — Vaganam | Priya Nair |
| vijay.chandran@vaganam.dev | 9 | Grade 9 — Vaganam | Priya Nair |
| asha.krishnan@vaganam.dev | 10 | Grade 10 — Vaganam | Arjun Menon |
| kavya.nair@vaganam.dev | 10 | Grade 10 — Vaganam | Arjun Menon |
| nikhil.pillai@vaganam.dev | 10 | Grade 10 — Vaganam | Arjun Menon |
| preethi.iyer@vaganam.dev | 10 | Grade 10 — Vaganam | Arjun Menon |
| siddharth.rao@vaganam.dev | 10 | Grade 10 — Vaganam | Arjun Menon |
| arvind.suresh@vaganam.dev | 11 | Grade 11 — Vaganam | Deepa Krishnan |
| gopal.menon@vaganam.dev | 11 | Grade 11 — Vaganam | Deepa Krishnan |
| harish.kumar@vaganam.dev | 11 | Grade 11 — Vaganam | Deepa Krishnan |
| parvathi.nair@vaganam.dev | 11 | Grade 11 — Vaganam | Deepa Krishnan |
| sowmya.raj@vaganam.dev | 11 | Grade 11 — Vaganam | Deepa Krishnan |
| lalitha.menon@vaganam.dev | 11 | Grade 11 — Humanities | Deepa Krishnan |
| rajan.iyer@vaganam.dev | 11 | Grade 11 — Humanities | Deepa Krishnan |
| geetha.varma@vaganam.dev | 12 | Grade 12 — Vaganam | Suresh Iyer |
| manoj.chandran@vaganam.dev | 12 | Grade 12 — Vaganam | Suresh Iyer |
| nithya.iyer@vaganam.dev | 12 | Grade 12 — Vaganam | Suresh Iyer |
| revathi.pillai@vaganam.dev | 12 | Grade 12 — Vaganam | Suresh Iyer |
| sunil.gopalan@vaganam.dev | 12 | Grade 12 — Vaganam | Suresh Iyer |

---

## Dev Magic Login (no password)

http://localhost:3000/dev-login — pick Student, Teacher, or School Admin instantly.

---

## Tailscale + Docker Fix

If localhost stops loading after Tailscale reconnects:

```bash
sudo tailscale up --accept-routes --exit-node=100.101.249.109 --operator=sivam --exit-node-allow-lan-access=true
```

Root cause: exit node routes all traffic including Docker's 172.18.x.x IPs through remote node.
`--exit-node-allow-lan-access=true` keeps local/private IPs routed locally.
