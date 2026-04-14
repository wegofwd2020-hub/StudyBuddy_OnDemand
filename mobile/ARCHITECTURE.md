# StudyBuddy Mobile App — Architecture Guide

> **Platform:** Android (primary) · iOS (secondary) · Desktop dev (Python/Kivy)
> **Framework:** Kivy 2.x · Python 3.11 · httpx (async HTTP) · SQLite (local storage)
> **Build tool:** Buildozer / python-for-android

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Layer Architecture](#2-layer-architecture)
3. [Persona: Student (Standard)](#3-persona-student-standard)
4. [Persona: Student (School-Enrolled)](#4-persona-student-school-enrolled)
5. [Persona: First-Time User](#5-persona-first-time-user)
6. [Offline-First Architecture](#6-offline-first-architecture)
7. [Authentication Flow](#7-authentication-flow)
8. [Content Delivery Pipeline](#8-content-delivery-pipeline)
9. [Progress & Analytics Flow](#9-progress--analytics-flow)
10. [Local Storage Architecture](#10-local-storage-architecture)
11. [Screen State Machine](#11-screen-state-machine)
12. [API Contract](#12-api-contract)
13. [Configuration & Secrets](#13-configuration--secrets)
14. [Build & Run](#14-build--run)

---

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      STUDYBUDDY SYSTEM                                  │
│                                                                         │
│  ┌─────────────────┐     HTTPS / JWT      ┌────────────────────────┐   │
│  │  MOBILE APP     │◄────────────────────►│   BACKEND API          │   │
│  │  (this repo)    │                      │   FastAPI + asyncpg    │   │
│  │                 │                      │   PgBouncer + Redis    │   │
│  │  Kivy / Python  │                      └───────────┬────────────┘   │
│  │  Android / iOS  │                                  │                │
│  │                 │      CDN (pre-signed URL)         │                │
│  │                 │◄─────────────────────────────────┤                │
│  │                 │      MP3 audio direct             │                │
│  └─────────────────┘                      ┌───────────▼────────────┐   │
│                                           │   PostgreSQL            │   │
│  The mobile app NEVER calls:              │   Redis                 │   │
│  • Anthropic API                          │   S3 / Content Store    │   │
│  • Stripe directly                        └────────────────────────┘   │
│  • Auth0 management API                                                 │
│                                                                         │
│  Auth0 is only used for the PKCE browser flow (student login).          │
└─────────────────────────────────────────────────────────────────────────┘
```

### What the mobile app does

| Responsibility | How |
|---|---|
| Student authentication | Auth0 PKCE → backend token exchange |
| Curriculum browsing | REST API + local SQLite cache |
| Lesson delivery | REST API → cache → display (text + audio) |
| Quiz taking | REST API → MCQ UI → fire-and-forget answer events |
| Progress tracking | EventQueue → SyncManager → backend (offline-safe) |
| Analytics | EventQueue → SyncManager → backend (fire-and-forget) |
| Subscription paywall | 402 intercept → Stripe Checkout (system browser) |
| Offline resilience | LocalCache (content) + EventQueue (events) |
| Multi-language | i18n loader (en / fr / es); AI content pre-translated |

### What the mobile app does NOT do

- Generate any AI content (no Anthropic key)
- Process Stripe payments directly (no Stripe key)
- Store student PII beyond name/email in JWT
- Make Auth0 management API calls
- Decide entitlement (backend is sole source of truth via HTTP status codes)

---

## 2. Layer Architecture

```
┌────────────────────────────────────────────────────────────┐
│                        UI LAYER                            │
│  mobile/src/ui/                                            │
│                                                            │
│  LoginScreen   DashboardScreen   CurriculumMapScreen       │
│  SubjectScreen  QuizScreen       TutorialScreen            │
│  ExperimentScreen  ResultScreen  SubscriptionScreen        │
│  SettingsScreen    StatsScreen   ProgressDashboardScreen   │
│                                                            │
│  Rules:                                                    │
│  • All network calls in daemon threads (never block loop)  │
│  • All UI mutations via @mainthread decorator              │
│  • Never import from another screen directly               │
│  • Navigate via ScreenManager only                         │
└────────────────────┬───────────────────────────────────────┘
                     │ imports ▼
┌────────────────────▼───────────────────────────────────────┐
│                      LOGIC LAYER                           │
│  mobile/src/logic/                                         │
│                                                            │
│  SyncManager    — flush EventQueue to backend              │
│  LocalCache     — SQLite LRU content cache (200 MB)        │
│  EventQueue     — SQLite offline event buffer              │
│  [ProgressQueue]  — session state buffer (not yet built)   │
│  [CurriculumResolver] — entitlement filter (not yet built) │
│                                                            │
│  Rules:                                                    │
│  • Never imports from ui/                                  │
│  • Thread-safe (threading.Lock on all SQLite ops)          │
│  • All methods synchronous (called from daemon threads)    │
└────────────────────┬───────────────────────────────────────┘
                     │ imports ▼
┌────────────────────▼───────────────────────────────────────┐
│                       API LAYER                            │
│  mobile/src/api/                                           │
│                                                            │
│  __init__.py         — shared header builders              │
│  auth_client.py      — Auth0 PKCE token exchange           │
│  content_client.py   — lesson / quiz / tutorial / audio    │
│  progress_client.py  — session / answer / dashboard        │
│  analytics_client.py — lesson_start / lesson_end           │
│  subscription_client.py — status / checkout / cancel       │
│                                                            │
│  Rules:                                                    │
│  • httpx.AsyncClient for all calls                         │
│  • Every request includes X-App-Version header             │
│  • Authenticated requests include Authorization: Bearer    │
│  • Never import from ui/ or logic/                         │
└────────────────────┬───────────────────────────────────────┘
                     │ HTTP ▼
┌────────────────────▼───────────────────────────────────────┐
│                    BACKEND REST API                        │
│  {BACKEND_URL}/api/v1/...                                  │
└────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                      UTILS LAYER                            │
│  mobile/src/utils/                                          │
│  i18n.py  — locale loader (en/fr/es), t() function         │
│  logger.py — structlog JSON logger (no print, no PII)      │
│                                                             │
│  Imported by all layers. No upward imports.                 │
└─────────────────────────────────────────────────────────────┘
```

### Dependency rules (enforced by convention)

```
ui/    →  logic/  →  api/  →  (HTTP)  →  backend
  ↘             ↘
   utils/       utils/
```

No layer may import from a layer above it. `utils/` is the only layer imported everywhere.

---

## 3. Persona: Student (Standard)

> A student with a direct subscription (not enrolled in a school). Grades 5–12.
> Pays individually. Uses the app independently.

### Journey map

```
START
  │
  ▼
┌──────────────────────────────────────────────────────────────────┐
│  ONBOARDING                                                      │
│                                                                  │
│  First launch → version check → LoginScreen                      │
│  → Auth0 browser PKCE flow                                       │
│  → /auth/exchange (backend issues internal JWT)                  │
│  → JWT stored to disk (0600 permissions)                         │
│  → DashboardScreen                                               │
└──────────────────────────────────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────────────────────────────────┐
│  DAILY SESSION                                                   │
│                                                                  │
│  DashboardScreen                                                 │
│    ├── Greeting + streak badge (from /student/dashboard)         │
│    ├── "Continue" card → last incomplete unit                    │
│    ├── Recent activity list (quiz scores, lessons viewed)        │
│    └── "Browse All Subjects" → CurriculumMapScreen              │
│                                                                  │
│  CurriculumMapScreen                                             │
│    ├── All subjects for the student's grade                      │
│    ├── Per-unit status badges:                                   │
│    │     ✅ completed   🔁 needs_retry                           │
│    │     ▶  in_progress  ○  not_started                          │
│    └── Tap unit → SubjectScreen                                  │
│                                                                  │
│  SubjectScreen                                                   │
│    ├── Lesson content (title, synopsis, key concepts)            │
│    ├── 🔊 Listen → fetches pre-signed CDN URL → MP3 playback    │
│    ├── 🔬 Experiment (shown only if unit has_lab = true)         │
│    └── 📝 Take Quiz → QuizScreen                                │
│                                                                  │
│  QuizScreen                                                      │
│    ├── MCQ, one question at a time                               │
│    ├── Instant colour feedback (green / red)                     │
│    ├── Answer recorded via EventQueue (fire-and-forget)          │
│    └── Last question → ResultScreen                              │
│                                                                  │
│  ResultScreen                                                    │
│    ├── Backend-confirmed score + attempt number                  │
│    ├── passed ≥ 60% → "Well done!" + back to map                 │
│    ├── failed < 60% → "Try again" + Tutorial shortcut            │
│    └── Retry path → TutorialScreen → QuizScreen                  │
└──────────────────────────────────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────────────────────────────────┐
│  PAYWALL (if subscription lapses)                                │
│                                                                  │
│  Any content endpoint returns HTTP 402                           │
│  → SubscriptionScreen                                            │
│  → Plan selection (Monthly / Annual)                             │
│  → POST /subscription/checkout → checkout_url                   │
│  → System browser opens Stripe Checkout                          │
│  → Stripe fires webhook → backend activates subscription         │
│  → Student taps "I've subscribed" → backend confirms → resume   │
└──────────────────────────────────────────────────────────────────┘
```

### Screen flow diagram

```
                     ┌─────────────┐
         App launch  │             │
        ────────────►│   Login     │
                     │   Screen    │
                     └──────┬──────┘
                            │ auth success
                            ▼
                     ┌─────────────┐
             ┌──────►│  Dashboard  │◄─────────────────────┐
             │       │  Screen     │                       │
             │       └──────┬──────┘                       │
             │              │ browse all / continue card    │
             │              ▼                              │
             │       ┌──────────────┐                      │
             │       │  Curriculum  │                      │
             │       │  Map Screen  │                      │
             │       └──────┬───────┘                      │
             │              │ tap unit                     │
             │              ▼                              │
             │       ┌──────────────┐                      │
             │       │   Subject    │──────┐               │
             │       │   Screen     │      │ experiment    │
             │       └──────┬───────┘      ▼               │
             │              │       ┌────────────┐         │
             │              │       │ Experiment │         │
             │              │       │   Screen   │         │
             │              │       └────────────┘         │
             │              │ take quiz                    │
             │              ▼                              │
             │       ┌──────────────┐                      │
             │       │    Quiz      │                      │
             │       │   Screen     │                      │
             │       └──────┬───────┘                      │
             │              │ last question                │
             │              ▼                              │
             │       ┌──────────────┐                      │
             │       │    Result    │──── passed ──────────┘
             │       │   Screen     │
             │       └──────┬───────┘
             │              │ failed → retry path
             │              ▼
             │       ┌──────────────┐
             │       │   Tutorial   │
             │       │   Screen     │
             │       └──────┬───────┘
             │              │ retry quiz
             └──────────────┘ (back to QuizScreen)

             Settings ──────────────────── from any screen (nav bar)
             Stats ─────────────────────── from Dashboard
             SubscriptionScreen ─────────── on HTTP 402 from any screen
```

---

## 4. Persona: Student (School-Enrolled)

> A student whose school has an active subscription. The school covers content access —
> the student pays nothing. The school controls which curriculum they follow.

### How school enrollment changes the experience

```
┌─────────────────────────────────────────────────────────────────┐
│  ENTITLEMENT DIFFERENCE                                         │
│                                                                 │
│  Standard student:                                              │
│    JWT → student_id, grade, locale, role: "student"             │
│    Backend checks: subscriptions table for active plan          │
│    No plan → HTTP 402 → SubscriptionScreen                      │
│                                                                 │
│  School-enrolled student:                                       │
│    JWT → student_id, grade, locale, role: "student"             │
│    Backend checks: school_enrolments → school_subscriptions     │
│    School has active plan → HTTP 200 (student pays nothing)     │
│    School has no plan → HTTP 402 (rare; handled same way)       │
│                                                                 │
│  The mobile app does NOT know which path was taken.             │
│  It only sees HTTP 200 (serve) or HTTP 402 (paywall).           │
│  Backend is the sole entitlement authority.                     │
└─────────────────────────────────────────────────────────────────┘
```

### Curriculum routing for school-enrolled students

```
Student logs in
      │
      ▼
Backend resolves curriculum:
  school.active_curriculum_id → grade_curriculum_assignments
      │
      ▼
GET /student/progress → curriculum_id = school's chosen curriculum
      │
      ▼
CurriculumMapScreen shows units from school curriculum
(not default platform curriculum)

┌─────────────────────────────────────────────────────────────────┐
│  Grade self-change is BLOCKED for school-enrolled students      │
│  (PATCH /student/profile returns 403 on grade field)            │
│  Grade is set exclusively by the school via teacher assignment  │
│  SettingsScreen hides the grade picker when school_id != NULL   │
└─────────────────────────────────────────────────────────────────┘
```

### Additional screens for school-enrolled students

```
DashboardScreen
  │
  └── Shows teacher name ("Assigned to: Ms. Johnson") if teacher assigned
      (student_teacher_assignments table → teacher name in JWT or dashboard payload)

SettingsScreen
  │
  ├── Language picker (always available)
  ├── Notification preferences (always available)
  ├── Grade picker (HIDDEN — school controls grade)
  └── "Contact your school to change grade" message instead
```

---

## 5. Persona: First-Time User

> A student opening the app for the first time. No JWT stored on device.
> May be under 13 (COPPA applies).

### Onboarding sequence

```
App Launch
  │
  ├── [1] Version check (daemon thread, non-blocking)
  │         GET /app/version (unauthenticated)
  │         ├── below min_version → blocking modal → update required
  │         ├── below latest_version → dismissible banner → update available
  │         └── current → no UI
  │
  ├── [2] Token check (main thread, instant)
  │         Read jwt.token from disk
  │         ├── found + valid → skip login → DashboardScreen
  │         └── not found / expired → LoginScreen
  │
  └── [3] LoginScreen (if no token)

         ┌───────────────────────────────────┐
         │         LOGIN SCREEN              │
         │                                   │
         │  ┌─────────────────────────────┐  │
         │  │  [Login with your school]   │  │  ← primary CTA
         │  └─────────────────────────────┘  │
         │                                   │
         │  [Create account]                 │  → Auth0 signup URL
         │  [Forgot password]                │  → Auth0 reset URL
         │                                   │
         └───────────────────────────────────┘
                         │
                         │ "Login" tapped
                         ▼
              Generate PKCE verifier + challenge
                         │
                         ▼
              Open system browser → Auth0 login page
                         │
                         ▼
              Student enters credentials in browser
                         │
                         ▼
              Auth0 redirects → studybuddy://callback?code=...
                         │
                         ▼
              App receives deep link → extract code
                         │
              ┌──────────┴───────────────────────┐
              │ exchange code with Auth0 → id_token│
              │ POST /auth/exchange → internal JWT  │
              │ Store JWT to disk (0600 perms)      │
              └──────────────────────────────────────┘
                         │
                         ▼
            ┌────────────────────────────────────┐
            │  HTTP 403 + "coppa" in body?        │
            │  → "Ask a parent to check email"    │
            │  → Stay on LoginScreen               │
            │                                      │
            │  HTTP 403 + "suspended"?             │
            │  → "Contact your school"             │
            │  → Stay on LoginScreen               │
            │                                      │
            │  Success → DashboardScreen           │
            └────────────────────────────────────┘

         COPPA path (under-13):
           ├── Parent receives consent email
           ├── Parent clicks link → consent form
           ├── Backend activates account (account_status = 'active')
           └── Student can now log in successfully
```

---

## 6. Offline-First Architecture

The app is designed to work without internet after the first content fetch.

### Offline capability matrix

```
Feature                │ Online  │ Offline (cached) │ Offline (no cache)
───────────────────────┼─────────┼──────────────────┼──────────────────────
View lesson text       │  ✅     │  ✅              │  ❌ "Download needed"
Listen to audio        │  ✅     │  ✅ (MP3 cached) │  ❌ hidden
View tutorial          │  ✅     │  ✅              │  ❌ "Download needed"
View experiment        │  ✅     │  ✅              │  ❌ hidden
Take quiz              │  ✅     │  ✅ (questions)   │  ❌ "Download needed"
Record quiz answers    │  ✅     │  ✅ (queued)      │  ✅ (queued in SQLite)
End quiz session       │  ✅     │  ⚠️ queued        │  ⚠️ queued
Dashboard              │  ✅     │  ✅ (stale)       │  ✅ (stale)
Curriculum map         │  ✅     │  ✅ (stale)       │  ✅ (stale)
Start new quiz session │  ✅     │  ❌ (needs API)   │  ❌ (ProgressQueue TODO)
```

### Offline sync architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    OFFLINE SYNC FLOW                                │
│                                                                     │
│  Student action (online or offline)                                 │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────────┐                                               │
│  │  Screen (UI)     │  Records event immediately (no wait)          │
│  │  QuizScreen      │─────────────────────────────┐                │
│  │  SubjectScreen   │                             │                │
│  └──────────────────┘                             ▼                │
│                                       ┌───────────────────────┐    │
│                                       │    EventQueue         │    │
│                                       │    (SQLite on device) │    │
│                                       │                       │    │
│                                       │  event_id (UUID)      │    │
│                                       │  event_type           │    │
│                                       │  payload (JSON)       │    │
│                                       │  created_at           │    │
│                                       │  sent_at (NULL=unsent)│    │
│                                       └───────────┬───────────┘    │
│                                                   │                │
│  Trigger: app foreground / network restore        │                │
│         │                                         │                │
│         ▼                                         │                │
│  ┌──────────────────┐    reads pending events     │                │
│  │  SyncManager     │◄────────────────────────────┘                │
│  │  (daemon thread) │                                              │
│  └──────┬───────────┘                                              │
│         │ dispatches per event_type                                │
│         │                                                          │
│  ┌──────▼──────────────────────────────────────┐                  │
│  │  Event routing                               │                  │
│  │                                              │                  │
│  │  progress_answer → POST /progress/session/   │                  │
│  │                        {id}/answer           │                  │
│  │                                              │                  │
│  │  lesson_end      → POST /analytics/lesson/   │                  │
│  │                        end                   │                  │
│  └──────────────────────────────────────────────┘                  │
│         │                                                          │
│         │ success → mark_sent(event_id)                            │
│         │ failure → leave in queue (retry on next flush)           │
│         │                                                          │
│         ▼                                                          │
│  Backend deduplicates by event_id                                  │
│  (ON CONFLICT DO NOTHING on event_id column)                       │
│                                                                    │
│  Old sent events purged after 7 days (keep_days=7)                 │
└─────────────────────────────────────────────────────────────────────┘
```

### Content cache architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CONTENT CACHE (LocalCache)                       │
│                                                                     │
│  Screen requests content                                            │
│         │                                                           │
│         ▼                                                           │
│  LocalCache.get(unit_id, curriculum_id, content_type, lang,        │
│                 content_version)                                    │
│         │                                                           │
│    ┌────┴──────────────────────────────────────────┐               │
│    │                                               │               │
│  HIT (version match)                         MISS or stale         │
│    │                                               │               │
│    ▼                                               ▼               │
│  Return dict                           Fetch from backend API       │
│  (no network cost)                              │                  │
│                                                 ▼                  │
│                                     LocalCache.put(...)            │
│                                                 │                  │
│                                                 ▼                  │
│                                     LRU eviction if >200 MB        │
│                                     (oldest last_accessed removed) │
│                                                                    │
│  SQLite schema: cached_content                                      │
│  ┌──────────────┬──────────────────┬──────────────┬──────────────┐ │
│  │ unit_id (PK) │ curriculum_id(PK)│content_type  │ lang (PK)    │ │
│  ├──────────────┼──────────────────┼──────────────┼──────────────┤ │
│  │ G8-MATH-001  │ default-2026-g8  │ lesson       │ en           │ │
│  │ G8-MATH-001  │ default-2026-g8  │ quiz         │ en           │ │
│  │ G8-MATH-001  │ default-2026-g8  │ tutorial     │ fr           │ │
│  │ G8-SCI-002   │ abc-school-uuid  │ experiment   │ en           │ │
│  └──────────────┴──────────────────┴──────────────┴──────────────┘ │
│  content_version INTEGER — stale entries auto-evicted on mismatch  │
│  last_accessed  TEXT    — used for LRU ordering                    │
│  Max size: 200 MB (configurable via MAX_CACHE_MB in config.py)     │
└─────────────────────────────────────────────────────────────────────┘
```

### Audio cache (separate from LocalCache)

```
Audio files are NOT stored in SQLite (too large).
They are cached on the filesystem:

  ~/.studybuddy/audio/{unit_id}_{curriculum_id}_{lang}.mp3

Flow:
  SubjectScreen → GET /content/{unit_id}/lesson/audio
               → backend returns pre-signed S3/CDN URL (not the MP3)
               → app downloads MP3 from CDN directly (not via backend)
               → saves to audio cache dir
               → Kivy SoundLoader plays from local file

On repeat visits: check filesystem cache first → skip CDN download
```

---

## 7. Authentication Flow

### Auth0 PKCE (all students)

```
┌──────────────────────────────────────────────────────────────────────┐
│                      AUTH0 PKCE FLOW                                 │
│                                                                      │
│  Mobile App                  System Browser          Backend          │
│      │                            │                     │            │
│      │ 1. Generate PKCE pair      │                     │            │
│      │    verifier (random 32B)   │                     │            │
│      │    challenge = SHA256(v)   │                     │            │
│      │                            │                     │            │
│      │ 2. Open URL in browser     │                     │            │
│      │──────────────────────────► │                     │            │
│      │    Auth0 /authorize?       │                     │            │
│      │    client_id=...           │                     │            │
│      │    code_challenge=...      │                     │            │
│      │    redirect_uri=           │                     │            │
│      │    studybuddy://callback   │                     │            │
│      │                            │                     │            │
│      │                            │ 3. Student logs in  │            │
│      │                            │    (Auth0 UI)       │            │
│      │                            │                     │            │
│      │ 4. Deep link received      │                     │            │
│      │◄──────────────────────────  │                     │            │
│      │ studybuddy://callback       │                     │            │
│      │   ?code=AUTH_CODE           │                     │            │
│      │                            │                     │            │
│      │ 5. Exchange code           │                     │            │
│      │    Auth0 /oauth/token       │                     │            │
│      │    + verifier               │                     │            │
│      │    → id_token               │                     │            │
│      │                            │                     │            │
│      │ 6. POST /auth/exchange     │                     │            │
│      │    {id_token}              │                     │            │
│      │───────────────────────────────────────────────► │            │
│      │                            │                     │            │
│      │                            │         7. Verify id_token      │
│      │                            │            with Auth0 JWKS      │
│      │                            │            Upsert student row   │
│      │                            │            Issue internal JWT   │
│      │                            │                     │            │
│      │ 8. Internal JWT returned   │                     │            │
│      │◄────────────────────────────────────────────────            │
│      │                            │                     │            │
│      │ 9. Store JWT to disk       │                     │            │
│      │    path: user_data_dir/    │                     │            │
│      │          jwt.token         │                     │            │
│      │    permissions: 0600       │                     │            │
│      │                            │                     │            │
│      │ 10. Navigate to Dashboard  │                     │            │
└──────────────────────────────────────────────────────────────────────┘
```

### Token lifecycle

```
┌──────────────────────────────────────────────────────────────────┐
│                    TOKEN LIFECYCLE                               │
│                                                                  │
│  Token file: {user_data_dir}/jwt.token (permissions: 0600)      │
│                                                                  │
│  App launch sequence:                                            │
│    1. Read jwt.token from disk                                   │
│    2. If missing → LoginScreen                                   │
│    3. If present → DashboardScreen (backend validates on use)    │
│    4. If any request returns 401 → LoginScreen (token expired)  │
│                                                                  │
│  JWT payload: {student_id, grade, locale, role: "student", exp} │
│                                                                  │
│  Token does NOT contain:                                         │
│    ✗ subscription status (checked via backend on each request)  │
│    ✗ school_id (resolved server-side)                           │
│    ✗ curriculum_id (resolved server-side)                       │
│                                                                  │
│  Sign-out:                                                       │
│    SettingsScreen → delete jwt.token → navigate to LoginScreen  │
│                                                                  │
│  Suspension:                                                     │
│    Backend sets Redis suspended:{student_id} key (no TTL)       │
│    Next API call returns 403 + "suspended" in body              │
│    App shows "Contact your school" error + stays on LoginScreen │
└──────────────────────────────────────────────────────────────────┘
```

---

## 8. Content Delivery Pipeline

```
┌──────────────────────────────────────────────────────────────────────┐
│              HOW CONTENT REACHES THE STUDENT                         │
│                                                                      │
│  [Content Pipeline — offline, operator-run]                          │
│                                                                      │
│  Admin runs build_grade.py                                           │
│       │                                                              │
│       ▼                                                              │
│  Anthropic Claude API generates:                                     │
│    lesson_{lang}.json                                                │
│    quiz_set_1_{lang}.json                                            │
│    tutorial_{lang}.json                                              │
│    experiment_{lang}.json  (only if has_lab = true)                  │
│       │                                                              │
│       ▼                                                              │
│  TTS worker converts lesson text → MP3                               │
│       │                                                              │
│       ▼                                                              │
│  Files written to S3 / Content Store:                                │
│    curricula/{curriculum_id}/{unit_id}/lesson_en.json               │
│    curricula/{curriculum_id}/{unit_id}/lesson_en.mp3                │
│    curricula/{curriculum_id}/{unit_id}/meta.json                    │
│       │                                                              │
│  [Backend API — always-on]                                           │
│       │                                                              │
│       ▼                                                              │
│  GET /content/{unit_id}/lesson                                       │
│    → L1 Redis (5 min TTL) → L2 S3 → return JSON                     │
│                                                                      │
│  GET /content/{unit_id}/lesson/audio                                 │
│    → return pre-signed CDN URL (not the MP3 bytes)                   │
│    → client downloads MP3 from CDN directly                          │
│                                                                      │
│  [Mobile App]                                                        │
│       │                                                              │
│       ▼                                                              │
│  SubjectScreen enters                                                │
│       │                                                              │
│       ├── Check LocalCache → HIT → render immediately               │
│       │                                                              │
│       └── MISS → GET /content/{unit_id}/lesson                      │
│                → backend checks entitlement                          │
│                   ├── 200 → content JSON returned                   │
│                   ├── 402 → navigate to SubscriptionScreen          │
│                   └── 403 → not enrolled / school no plan           │
│                → LocalCache.put() → render                          │
└──────────────────────────────────────────────────────────────────────┘

Content types per unit:
  ┌───────────────┬──────────────────────────────────────────────────┐
  │ Type          │ Screen            │ Cached? │ Always present?     │
  ├───────────────┼───────────────────┼─────────┼─────────────────────┤
  │ lesson        │ SubjectScreen     │ Yes     │ Yes                 │
  │ audio (MP3)   │ SubjectScreen     │ Yes (FS)│ Yes                 │
  │ quiz          │ QuizScreen        │ Yes     │ Yes                 │
  │ tutorial      │ TutorialScreen    │ Yes     │ Yes                 │
  │ experiment    │ ExperimentScreen  │ Yes     │ Only if has_lab=true│
  └───────────────┴───────────────────┴─────────┴─────────────────────┘
```

---

## 9. Progress & Analytics Flow

### Quiz session lifecycle

```
┌──────────────────────────────────────────────────────────────────────┐
│                    QUIZ SESSION LIFECYCLE                            │
│                                                                      │
│  QuizScreen.set_context(token, unit_id, curriculum_id, lang)         │
│         │                                                            │
│         ▼                                                            │
│  POST /progress/session                                              │
│    → server returns {session_id, attempt_number}                     │
│    → attempt_number is ALWAYS server-computed (never trust client)   │
│         │                                                            │
│  ┌──────▼──────────────────────────────────┐                        │
│  │  For each question (1 to N):            │                        │
│  │                                         │                        │
│  │  Student taps answer                    │                        │
│  │         │                               │                        │
│  │         ▼                               │                        │
│  │  Show immediate feedback                │                        │
│  │  (green = correct, red = incorrect)     │                        │
│  │         │                               │                        │
│  │         ▼                               │                        │
│  │  EventQueue.enqueue(                    │                        │
│  │    "progress_answer", {                 │                        │
│  │      session_id,                        │                        │
│  │      question_id,                       │                        │
│  │      student_answer,                    │                        │
│  │      correct_answer,                    │                        │
│  │      correct,                           │                        │
│  │      ms_taken                           │                        │
│  │    }                                    │                        │
│  │  )                                      │                        │
│  │  → fire-and-forget; UI never waits      │                        │
│  │         │                               │                        │
│  │  Advance to next question               │                        │
│  └─────────────────────────────────────────┘                        │
│         │                                                            │
│         ▼                                                            │
│  POST /progress/session/{id}/end                                     │
│    {score, total_questions}                                          │
│    → server returns {score, passed, attempt_number}                  │
│    → navigate to ResultScreen with backend-confirmed data            │
│                                                                      │
│  SyncManager (triggered in background)                               │
│    → flushes queued progress_answer events to backend               │
│    → backend deduplicates via event_id ON CONFLICT DO NOTHING        │
└──────────────────────────────────────────────────────────────────────┘
```

### Lesson analytics flow

```
┌──────────────────────────────────────────────────────────────────────┐
│                    LESSON VIEW ANALYTICS                             │
│                                                                      │
│  SubjectScreen.on_enter()                                            │
│         │                                                            │
│         ▼                                                            │
│  POST /analytics/lesson/start                                        │
│    → server returns {view_id}                                        │
│    → record start_time = time.time()                                 │
│    → record view_id in screen state                                  │
│                                                                      │
│  Student interacts:                                                  │
│    └── taps 🔊 Listen   → audio_played = True                       │
│    └── taps 🔬 Experiment → experiment_viewed = True                │
│                                                                      │
│  SubjectScreen.on_leave()                                            │
│         │                                                            │
│         ▼                                                            │
│  EventQueue.enqueue(                                                 │
│    "lesson_end", {                                                   │
│      view_id,                                                        │
│      duration_s = time.time() - start_time,                         │
│      audio_played,                                                   │
│      experiment_viewed                                               │
│    }                                                                 │
│  )                                                                   │
│  → fire-and-forget; screen transitions immediately                   │
│                                                                      │
│  SyncManager flushes later:                                          │
│    → POST /analytics/lesson/end {view_id, duration_s, ...}          │
└──────────────────────────────────────────────────────────────────────┘
```

### Streak tracking

```
Streak lives in Redis on the backend, not on the mobile device.

  Session end (POST /progress/session/{id}/end)
       │
       ▼
  Backend Celery task: update_streak_task
       │
       ▼
  Redis key "streak:{student_id}" updated:
    {current: N, longest: M, last_active_date: "YYYY-MM-DD"}
       │
       ▼
  GET /student/dashboard → streak returned in payload
       │
       ▼
  DashboardScreen displays "🔥 N-day streak"
```

---

## 10. Local Storage Architecture

```
Device filesystem layout:

  {user_data_dir}/          ← Kivy-managed, app-private directory
    studybuddy.db           ← SQLite: LocalCache + EventQueue tables
    jwt.token               ← Internal JWT (0600 permissions)
    refresh.token           ← Refresh token (0600 permissions)

  ~/.studybuddy/audio/      ← MP3 audio cache (filesystem, not SQLite)
    {unit_id}_{curriculum_id}_{lang}.mp3

SQLite tables:

  ┌─────────────────────────────────────────────────────────────────┐
  │  cached_content                (managed by LocalCache)          │
  ├──────────────────┬─────────────────────────────────────────────┤
  │  unit_id (PK)    │  TEXT NOT NULL                               │
  │  curriculum_id(PK)│ TEXT NOT NULL                               │
  │  content_type(PK)│  TEXT NOT NULL                               │
  │  lang (PK)       │  TEXT NOT NULL                               │
  │  content_version │  INTEGER NOT NULL                            │
  │  data            │  TEXT NOT NULL  (JSON blob)                  │
  │  cached_at       │  TEXT (datetime)                             │
  │  last_accessed   │  TEXT (datetime) — LRU key                  │
  └──────────────────┴─────────────────────────────────────────────┘
  Max size: 200 MB. LRU eviction when exceeded.
  Version mismatch auto-evicts stale entries.

  ┌─────────────────────────────────────────────────────────────────┐
  │  event_queue                   (managed by EventQueue)          │
  ├──────────────────┬─────────────────────────────────────────────┤
  │  event_id (PK)   │  TEXT  — UUID, used for backend dedup        │
  │  event_type      │  TEXT  — 'progress_answer' | 'lesson_end'   │
  │  payload         │  TEXT  — JSON blob                           │
  │  created_at      │  TEXT  — ISO 8601 UTC                        │
  │  sent_at         │  TEXT  — NULL until delivered; purged @7d    │
  └──────────────────┴─────────────────────────────────────────────┘
  Max queue depth: 1000 events (MAX_QUEUE_SIZE in config.py)
  Retention: sent events purged after 7 days

  ┌─────────────────────────────────────────────────────────────────┐
  │  [TODO] progress_sessions      (managed by ProgressQueue)       │
  │  — session state buffer for offline quiz start                  │
  │  — not yet implemented                                          │
  └─────────────────────────────────────────────────────────────────┘
```

---

## 11. Screen State Machine

```
                              ┌─────────────────────────────────────┐
                              │         STARTUP                     │
                              │  version check (daemon thread)      │
                              │  token check (main thread)          │
                              └────────────┬────────────────────────┘
                                           │
                          ┌────────────────┴───────────────┐
                          │ token missing                  │ token present
                          ▼                                ▼
                   ┌─────────────┐                  ┌─────────────────┐
                   │   LOGIN     │                  │   DASHBOARD     │
                   │             │                  │                 │
                   │  States:    │                  │  Stale-while-   │
                   │  default    │                  │  revalidate     │
                   │  waiting    │                  └────────┬────────┘
                   │  loading    │                           │
                   │  error      │    ┌──────────────────────┤
                   └──────┬──────┘    │                      │
                          │ success   │ browse all     from nav
                          └─────────►┤                      │
                                     ▼                      │
                              ┌──────────────┐              │
                              │  CURRICULUM  │              │
                              │  MAP         │              │
                              └──────┬───────┘              │
                                     │ tap unit             │
                                     ▼                      │
                              ┌──────────────┐              │
                              │  SUBJECT     │◄─────────────┘
                              │              │  (continue card)
                              └──┬─────┬─────┘
                                 │     │
                        quiz ────┘     └──── experiment
                                 │            │
                                 ▼            ▼
                         ┌───────────┐  ┌──────────────┐
                         │   QUIZ    │  │  EXPERIMENT  │
                         └─────┬─────┘  └──────────────┘
                               │ last Q
                               ▼
                         ┌───────────┐
                         │  RESULT   │
                         └─────┬─────┘
                               │
               ┌───────────────┴──────────────┐
               │ passed                        │ failed
               ▼                              ▼
         back to MAP                    ┌──────────────┐
                                        │  TUTORIAL    │
                                        └──────┬───────┘
                                               │ retry
                                               ▼
                                         back to QUIZ

  Global states (accessible from any screen via nav bar):
    SETTINGS    — language, notifications, sign-out
    STATS       — usage stats by period
    SUBSCRIPTION — on HTTP 402 from any content screen

  402 (paywall) can interrupt any content screen:
    SUBJECT → 402 → SUBSCRIPTION
    QUIZ    → 402 → SUBSCRIPTION
```

---

## 12. API Contract

All requests from the mobile app include:

```
Headers (authenticated):
  Authorization: Bearer {internal_jwt}
  X-App-Version: {APP_VERSION}     ← enforced by backend middleware

Headers (unauthenticated):
  X-App-Version: {APP_VERSION}

Backend response codes the mobile app must handle:
  200  OK — serve content
  201  Created — session started
  401  Unauthorized — JWT missing or invalid → LoginScreen
  402  Payment Required — no active subscription → SubscriptionScreen
  403  Forbidden — suspended / COPPA / school scope violation
  404  Not Found — content doesn't exist (experiment probe)
  409  Conflict — session already ended
  422  Validation error — bad request body
  426  Upgrade Required — X-App-Version below minimum → blocking modal
  5xx  Server error — show "Something went wrong" + retry option
```

### Endpoint map

```
Authentication
  POST /auth/exchange          id_token → internal JWT

Content (require JWT)
  GET  /content/{unit_id}/lesson        → lesson JSON
  GET  /content/{unit_id}/quiz          → quiz JSON (rotates sets 1→2→3)
  GET  /content/{unit_id}/tutorial      → tutorial JSON
  GET  /content/{unit_id}/experiment    → experiment JSON (404 if no lab)
  GET  /content/{unit_id}/lesson/audio  → {audio_url: "https://cdn..."} (pre-signed)

Progress (require JWT)
  POST /progress/session                → {session_id, attempt_number}
  POST /progress/session/{id}/answer   → {answer_id, correct}
  POST /progress/session/{id}/end      → {score, total_questions, passed}
  GET  /progress/student               → session history

Student (require JWT)
  GET  /student/dashboard              → summary + subject_progress + recent_activity
  GET  /student/progress               → curriculum map with status badges
  GET  /student/stats?period=7d|30d|all → usage stats + daily_activity

Analytics (require JWT)
  POST /analytics/lesson/start         → {view_id}
  POST /analytics/lesson/end           → 200 OK (fire-and-forget)

Subscription (require JWT)
  GET  /subscription/status            → {plan, status, current_period_end}
  POST /subscription/checkout          → {checkout_url} → open in browser
  POST /subscription/cancel            → 200 OK

Push notifications (require JWT)
  POST /notifications/token            → register FCM/APNs token
  DELETE /notifications/token          → unregister on logout
  GET  /notifications/preferences      → {quiz_results, daily_reminder, ...}
  PATCH /notifications/preferences     → update prefs

App version (unauthenticated)
  GET  /app/version                    → {min_version, latest_version}
```

---

## 13. Configuration & Secrets

```
config.py — ALL values, NO secrets

  APP_VERSION         = "2.0.0"
  BACKEND_URL         = os.getenv("STUDYBUDDY_BACKEND_URL", "http://localhost:8000")
  AUTH0_DOMAIN        = os.getenv("AUTH0_DOMAIN", "your-tenant.auth0.com")
  AUTH0_CLIENT_ID     = os.getenv("AUTH0_CLIENT_ID", "...")   ← public (PKCE)
  AUTH0_REDIRECT_URI  = "studybuddy://callback"
  SQLITE_DB_PATH      = None  (set at runtime from Kivy user_data_dir)
  JWT_STORAGE_FILENAME = "jwt.token"
  MAX_CACHE_MB        = 200
  SYNC_RETRY_INTERVAL_SECONDS = 30
  MAX_QUEUE_SIZE      = 1000

Keys intentionally absent (never in mobile):
  ✗ ANTHROPIC_API_KEY      — pipeline only
  ✗ STRIPE_SECRET_KEY      — backend only
  ✗ STRIPE_PUBLISHABLE_KEY — not needed (Checkout hosted page)
  ✗ ADMIN_JWT_SECRET       — backend only
  ✗ DATABASE_URL           — backend only

Environment variables for development:
  STUDYBUDDY_BACKEND_URL=http://localhost:8000
  AUTH0_DOMAIN=dev-tenant.auth0.com
  AUTH0_CLIENT_ID=dev-client-id
```

---

## 14. Build & Run

### Development (desktop)

```bash
# Install dependencies
pip install -r mobile/requirements.txt

# Run on desktop (no Android emulator needed)
cd mobile
STUDYBUDDY_BACKEND_URL=http://localhost:8000 \
AUTH0_DOMAIN=dev-tenant.auth0.com \
AUTH0_CLIENT_ID=dev-client-id \
python main.py

# Run tests (no display server required)
cd mobile
python -m pytest tests/ -v
```

### Android build (buildozer)

```bash
# Install buildozer
pip install buildozer

# First build (takes 20+ minutes — downloads NDK/SDK)
cd mobile
buildozer android debug

# Install to connected device
buildozer android deploy run

# View logs
buildozer android logcat | grep StudyBuddy
```

### Deep-link setup (Android)

Add to `AndroidManifest.xml` (via `buildozer.spec`):

```xml
<intent-filter>
    <action android:name="android.intent.action.VIEW" />
    <category android:name="android.intent.category.DEFAULT" />
    <category android:name="android.intent.category.BROWSABLE" />
    <data android:scheme="studybuddy" android:host="callback" />
</intent-filter>
```

The `AUTH0_REDIRECT_URI = "studybuddy://callback"` in `config.py` must match
the callback URL registered in the Auth0 application settings.

### Desktop dev workaround (no deep-link)

On desktop, the Auth0 redirect goes to `studybuddy://callback` which the OS
cannot open. LoginScreen detects this and switches to a manual paste mode:

```
Auth0 browser opens → student completes login → browser shows redirect URL
LoginScreen (waiting state) shows a text input field:
  "Paste the callback URL from your browser here"
Student copies the URL from the browser address bar → pastes → continue
```

---

## Known Gaps (as of 2026-04-11)

| Gap | Impact | Priority |
|---|---|---|
| `ProgressQueue` not implemented | Quiz sessions cannot be started offline; offline quiz retry broken | High |
| `CurriculumResolver` not implemented | No client-side entitlement filtering; all units shown regardless of subscription; backend enforces via HTTP 402 on tap | High |
| No automatic network state listener | SyncManager only flushes on app resume (manual trigger); events not flushed immediately when Wi-Fi reconnects | Medium |
| No centralized error types | Error handling spread across screen files; no exponential backoff or circuit breaker | Medium |
| No `mobile/README.md` | Build/run/test instructions absent; onboarding friction for new developers | Low |
| `auth0_client.py` is empty stub | Auth0 integration done inline in LoginScreen; module creates confusion | Low |
