# StudyBuddy Web — Test Cases

**Generated:** 2026-03-27
**Build:** 56 routes · 99 unit tests · 34 E2E tests
**Portals:** Public · Student · School · Admin

**Automated column key**
`E2E` = covered by Playwright (`npm run test:e2e`)
`Unit` = covered by Vitest (`npm test`)
`—` = manual only

---

## 1. Public Pages

### 1.1 Landing Page (`/`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| PUB-01 | Home banner displays at top | None | Navigate to `/` | Banner image visible at top of page, ~240 px tall, full width | E2E |
| PUB-02 | Hero heading is visible | None | Navigate to `/` | H1 heading renders above the fold | E2E |
| PUB-03 | Primary CTA navigates to signup | None | Click "Start free trial" | Redirects to `/signup` | E2E |
| PUB-04 | Secondary CTA scrolls to features | None | Click "See how it works" | Page scrolls to `#features` section | — |
| PUB-05 | Features grid renders 6 cards | None | Navigate to `/` and scroll down | 6 feature cards visible (Instant, Audio, Multilingual, Offline, Experiments, Schools) | — |
| PUB-06 | Testimonials section renders | None | Scroll to social proof section | 3 testimonial cards visible | — |
| PUB-07 | Footer CTA navigates to signup | None | Scroll to bottom; click "Start your free trial" | Redirects to `/signup` | — |
| PUB-08 | Nav Pricing link works | None | Click "Pricing" in nav | Redirects to `/pricing` | E2E |
| PUB-09 | Nav Sign in link works | None | Click "Sign in" in nav | Redirects to `/login` | E2E |
| PUB-10 | Mobile nav renders | Viewport < 768 px | Resize to mobile; navigate to `/` | Hamburger menu or mobile nav visible | — |

---

### 1.2 Pricing Page (`/pricing`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| PUB-11 | Three plan cards render | None | Navigate to `/pricing` | Free ($0), Student ($9.99), School ($299+) cards visible | E2E |
| PUB-12 | Free plan CTA goes to signup | None | Click "Start free" on Free plan | Redirects to `/signup` | — |
| PUB-13 | Student plan CTA goes to signup | None | Click "Subscribe now" on Student plan | Redirects to `/signup` | — |
| PUB-14 | School plan CTA goes to contact | None | Click "Contact sales" | Redirects to `/contact` | — |
| PUB-15 | FAQ accordion opens/closes | None | Click any FAQ question | Answer expands; click again to collapse | — |
| PUB-16 | Student plan marked "Most popular" | None | Navigate to `/pricing` | Visible badge on Student plan card | — |

---

### 1.3 Student Login Page (`/login`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| PUB-17 | Sign-in button renders | None | Navigate to `/login` | "Sign in with school account" Auth0 button visible | E2E |
| PUB-18 | Sign up link present | None | Navigate to `/login` | "Sign up free" link to `/signup` visible | — |

---

### 1.4 School Login Page (`/school/login`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| PUB-19 | School sign-in button renders | None | Navigate to `/school/login` | "Sign in with school account" button visible | E2E |
| PUB-20 | Link to student login | None | Navigate to `/school/login` | "Student login" link points to `/login` | E2E |
| PUB-21 | Link to contact us | None | Navigate to `/school/login` | "Contact us" link points to `/contact` | E2E |

---

### 1.5 Static Pages

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| PUB-22 | Terms of Service renders | None | Navigate to `/terms` | "Terms of Service" heading visible | E2E |
| PUB-23 | Privacy Policy renders | None | Navigate to `/privacy` | "Privacy Policy" heading visible | E2E |
| PUB-24 | Contact form renders | None | Navigate to `/contact` | "Send Message" button visible | E2E |
| PUB-25 | Signup page renders | None | Navigate to `/signup` | Signup form or Auth0 flow initiates | — |
| PUB-26 | 404 page for unknown route | None | Navigate to `/nonexistent-page` | HTTP 404; "Page not found" text visible | E2E |
| PUB-27 | COPPA consent page renders | None | Navigate to `/consent` | Parental consent form visible | — |
| PUB-28 | Reset password page renders | None | Navigate to `/reset-password` | Reset password form visible | — |

---

## 2. Student Portal

> **Auth note:** All student portal routes require an Auth0 session. Without one, the server-side layout redirects to `/login`.

### 2.1 Auth Redirects

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| STU-01 | Unauthenticated `/dashboard` redirects | No session | Navigate to `/dashboard` | Redirects to `/login` | E2E |
| STU-02 | Unauthenticated `/subjects` redirects | No session | Navigate to `/subjects` | Redirects to `/login` | E2E |
| STU-03 | Unauthenticated `/lesson/x` redirects | No session | Navigate to `/lesson/unit-001` | Redirects to `/login` | — |

---

### 2.2 Student Dashboard (`/dashboard`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| STU-04 | Dashboard loads with streak card | Logged in | Navigate to `/dashboard` | Streak card renders with day count | — |
| STU-05 | Quick action buttons navigate | Logged in | Click "Browse Subjects" | Redirects to `/subjects` | — |
| STU-06 | Quick action Curriculum Map | Logged in | Click "Curriculum Map" | Redirects to `/curriculum` | — |
| STU-07 | Quick action View Progress | Logged in | Click "View Progress" | Redirects to `/progress` | — |
| STU-08 | Recent activity shows sessions | Logged in + sessions exist | View dashboard | Up to 5 recent sessions listed with title, subject, date | — |
| STU-09 | Empty state if no sessions | Logged in + no sessions | View dashboard | Empty state message shown instead of activity list | — |
| STU-10 | Loading skeleton during fetch | Logged in | Navigate to `/dashboard` (slow network) | Skeleton placeholders render before data arrives | — |
| STU-11 | Offline banner shows when offline | Logged in + offline | Disable network; navigate to `/dashboard` | Offline banner visible at top | Unit |

---

### 2.3 Subjects Page (`/subjects`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| STU-12 | Subject list renders for grade | Logged in | Navigate to `/subjects` | Subject cards for student's grade displayed | — |
| STU-13 | Clicking subject opens units | Logged in | Click a subject card | Subject expands to show units | — |
| STU-14 | Paywall shown for locked content | Free plan + unit locked | Click locked unit | Redirected to `/paywall` | — |

---

### 2.4 Lesson Page (`/lesson/[unit_id]`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| STU-15 | Lesson content loads | Logged in + subscribed | Navigate to `/lesson/unit-001` | Lesson text visible | — |
| STU-16 | Audio player renders | Logged in + subscribed | Navigate to lesson page | Audio play button visible | — |
| STU-17 | Navigation to quiz available | Logged in + lesson loaded | Scroll to bottom of lesson | "Take quiz" or similar CTA visible | — |
| STU-18 | Paywall for free plan | Free plan + premium unit | Navigate to lesson | Redirected to `/paywall` (402 response) | — |

---

### 2.5 Quiz Page (`/quiz/[unit_id]`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| STU-19 | Quiz question renders | Logged in + subscribed | Navigate to `/quiz/unit-001` | Multiple choice question with 4 options visible | — |
| STU-20 | Selecting answer enables submit | Logged in | Click an answer option | Option highlighted; next/confirm button enabled | — |
| STU-21 | Correct answer shown after submit | Logged in | Select correct answer; submit | Correct answer highlighted in green | Unit |
| STU-22 | Wrong answer shown after submit | Logged in | Select wrong answer; submit | Correct answer revealed; wrong answer highlighted red | Unit |
| STU-23 | Score shown at end of quiz | Logged in | Complete all questions | Score screen shows X/Y correct | Unit |
| STU-24 | Session starts on page load | Logged in | Navigate to quiz page | Session initialises (no visible error) | — |
| STU-25 | Loading skeleton during init | Logged in | Navigate to quiz page | Skeleton shown while session loads | — |

---

### 2.6 Tutorial Page (`/tutorial/[unit_id]`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| STU-26 | Tutorial content loads | Logged in + subscribed | Navigate to `/tutorial/unit-001` | Step-by-step tutorial content visible | — |

---

### 2.7 Experiment Page (`/experiment/[unit_id]`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| STU-27 | Experiment steps render | Logged in + lab unit | Navigate to `/experiment/unit-001` | Materials, safety notes, numbered steps visible | — |
| STU-28 | Non-lab unit shows 404 | Logged in + non-lab unit | Navigate to experiment for non-lab unit | 404 or error state | — |

---

### 2.8 Progress Page (`/progress`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| STU-29 | Progress history renders | Logged in | Navigate to `/progress` | List of completed units with scores | — |
| STU-30 | Empty state if no history | Logged in + no history | Navigate to `/progress` | Empty state message | — |

---

### 2.9 Stats Page (`/stats`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| STU-31 | Usage stats render | Logged in | Navigate to `/stats` | Streak, total sessions, subject breakdown visible | — |

---

### 2.10 Curriculum Map (`/curriculum`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| STU-32 | Curriculum tree renders | Logged in | Navigate to `/curriculum` | Grade → Subject → Unit hierarchy visible | — |
| STU-33 | Completed units marked | Logged in + history | Navigate to `/curriculum` | Completed units show a tick or different styling | — |

---

### 2.11 Paywall (`/paywall`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| STU-34 | Paywall page renders | Free plan | Navigate to `/paywall` | Upgrade prompt with subscription link | — |
| STU-35 | Upgrade button navigates | Free plan | Click upgrade CTA | Redirects to `/account/subscription` | — |

---

### 2.12 Account Settings (`/account/settings`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| STU-36 | Settings load with current values | Logged in | Navigate to `/account/settings` | Display name, locale and notification prefs pre-filled | — |
| STU-37 | Display name can be updated | Logged in | Change name; click Save | Success confirmation appears | — |
| STU-38 | Language selection works | Logged in | Click "Français"; click Save | Locale saved; page reflects new language | — |
| STU-39 | Notification toggles save | Logged in | Toggle a notification checkbox; click Save | Preference saved without error | — |
| STU-40 | Loading skeleton during fetch | Logged in | Navigate to settings | Skeleton shown before data arrives | — |
| STU-41 | Error state on save failure | Logged in + backend down | Click Save | Error message shown | — |

---

### 2.13 Subscription Page (`/account/subscription`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| STU-42 | Current plan shown | Logged in | Navigate to subscription page | Active plan (Free / Monthly / Annual) displayed | — |
| STU-43 | Upgrade initiates Stripe checkout | Free plan | Click "Upgrade" | Redirected to Stripe checkout session | — |
| STU-44 | Billing portal opens for paid plan | Paid plan | Click "Manage billing" | Stripe billing portal opens | — |
| STU-45 | Trial days remaining shown | Trial active | Navigate to subscription | Trial days remaining displayed | Unit |

---

### 2.14 Subscription Success (`/account/subscription/success`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| STU-46 | Success page renders | After Stripe checkout | Navigate to `/account/subscription/success` | Success icon + confirmation message shown | — |
| STU-47 | Link to dashboard present | Success page | View page | "Go to dashboard" link visible | — |

---

### 2.15 Enrolment Confirmation (`/enrol/[token]`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| STU-48 | Valid token shows success | Valid enrolment token | Navigate to `/enrol/valid-token` | Success: school name displayed | — |
| STU-49 | Invalid token shows error | Invalid token | Navigate to `/enrol/bad-token` | Error message shown | — |
| STU-50 | Loading state during confirmation | Valid token | Navigate to page | Loading skeleton while API resolves | — |

---

## 3. School Portal

> **Auth note:** All school portal routes require an Auth0 session. Without one, the server-side layout redirects to `/school/login`.

### 3.1 Auth Redirects

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| SCH-01 | Unauthenticated `/school/dashboard` redirects | No session | Navigate to `/school/dashboard` | Redirects to `/school/login` | E2E |
| SCH-02 | Unauthenticated `/school/reports/overview` redirects | No session | Navigate to `/school/reports/overview` | Redirects to `/school/login` | E2E |

---

### 3.2 School Dashboard (`/school/dashboard`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| SCH-03 | Dashboard loads | Logged in as teacher | Navigate to `/school/dashboard` | KPI cards (active students, avg score, alerts) visible | — |
| SCH-04 | SchoolNav is visible | Logged in | Navigate to dashboard | Sidebar with nav items visible | — |
| SCH-05 | At-risk alert count shown | Logged in + alerts | View dashboard | Alert count badge in nav | — |

---

### 3.3 Class Overview (`/school/class/[class_id]`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| SCH-06 | Student list renders | Logged in | Navigate to class overview | Students listed with latest activity | — |
| SCH-07 | Click student opens student detail | Logged in | Click student row | Navigates to `/school/student/[student_id]` | — |

---

### 3.4 Student Detail (`/school/student/[student_id]`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| SCH-08 | Student profile and history loads | Logged in | Navigate to student detail | Student name, progress history, scores visible | — |

---

### 3.5 Reports — Overview (`/school/reports/overview`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| SCH-09 | Overview report loads | Logged in | Navigate to reports/overview | Class summary metrics (pass rate, active students, avg score) | — |
| SCH-10 | Reports sub-nav is visible | Logged in on any report | View page | Sub-nav links (Trends, At-Risk, Units, Engagement, Feedback, Export) visible | — |

---

### 3.6 Reports — Trends (`/school/reports/trends`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| SCH-11 | Trends chart renders | Logged in | Navigate to trends | Line chart with weekly pass-rate data visible | — |

---

### 3.7 Reports — At-Risk (`/school/reports/at-risk`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| SCH-12 | At-risk student table renders | Logged in | Navigate to at-risk | Students below threshold listed with scores | — |
| SCH-13 | Empty state if no at-risk students | Logged in + all passing | Navigate to at-risk | "No at-risk students" message shown | — |

---

### 3.8 Reports — Unit Performance (`/school/reports/units`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| SCH-14 | Unit performance chart renders | Logged in | Navigate to reports/units | Bar chart with per-unit pass rates visible | — |

---

### 3.9 Reports — Engagement (`/school/reports/engagement`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| SCH-15 | Engagement metrics render | Logged in | Navigate to engagement | Session counts, avg duration, active days visible | — |

---

### 3.10 Reports — Feedback (`/school/reports/feedback`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| SCH-16 | Student feedback list renders | Logged in | Navigate to reports/feedback | Student ratings and comments listed | — |

---

### 3.11 Reports — Export CSV (`/school/reports/export`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| SCH-17 | Export form renders | Logged in | Navigate to export page | Report type selector and "Export" button visible | — |
| SCH-18 | CSV download triggers | Logged in | Select report type; click Export | CSV file downloads with correct headers | Unit |

---

### 3.12 Alerts (`/school/alerts`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| SCH-19 | Alerts list renders | Logged in | Navigate to `/school/alerts` | Alert items listed with type, student name, date | — |
| SCH-20 | Dismissing alert updates list | Logged in + alert exists | Click dismiss on an alert | Alert removed from list immediately (optimistic) | Unit |
| SCH-21 | Unread count badge in nav | Logged in + unread alerts | Navigate anywhere in school portal | Red badge count on Alerts nav item | — |

---

### 3.13 Digest Settings (`/school/digest`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| SCH-22 | Digest settings form renders | Logged in | Navigate to `/school/digest` | Email field and day-of-week selector visible | — |
| SCH-23 | Subscribe saves preferences | Logged in | Fill email; click Subscribe | Success confirmation shown | — |

---

### 3.14 Curriculum Upload (`/school/curriculum`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| SCH-24 | Upload form renders | Logged in | Navigate to `/school/curriculum` | Grade dropdown, year input, file picker visible | — |
| SCH-25 | Template download works | Logged in | Click "Download XLSX template" | XLSX file downloaded | — |
| SCH-26 | Successful upload triggers pipeline | Logged in | Select valid XLSX; click Upload | Redirects to `/school/curriculum/pipeline/{job_id}` | Unit |
| SCH-27 | Per-row error table on bad file | Logged in | Upload invalid XLSX | Error table shows row number, field, and message | Unit |
| SCH-28 | Row 0 errors shown as file-level | Logged in | Upload structurally invalid XLSX | Row displayed as "—" in error table | Unit |
| SCH-29 | Upload button disabled during submit | Logged in | Click Upload | Button shows spinner; disabled until response | — |

---

### 3.15 Pipeline Status (`/school/curriculum/pipeline/[job_id]`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| SCH-30 | Progress bar renders | Job in progress | Navigate to pipeline page | Blue progress bar with percentage | — |
| SCH-31 | Progress bar auto-updates | Job in progress | Wait on page | Progress bar advances every 5 seconds | Unit |
| SCH-32 | Done state shows green bar | Job complete | Navigate to pipeline page | Green progress bar at 100% + success icon | Unit |
| SCH-33 | Failed state shows red indicator | Job failed | Navigate to pipeline page | Red indicator + failure count shown | Unit |
| SCH-34 | Polling stops on done/failed | Job done or failed | Wait on page | No more API requests after terminal state | Unit |

---

### 3.16 Student Roster (`/school/students`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| SCH-35 | Roster table renders | Logged in | Navigate to `/school/students` | Students listed with email, status, date | — |
| SCH-36 | Invite link displays and is copyable | Logged in | View page | Invite URL shown; "Copy" button works with 2 s feedback | Unit |
| SCH-37 | Bulk email enrol — newline separated | Logged in | Enter emails one per line; click Enrol | Students enrolled; success count shown | Unit |
| SCH-38 | Bulk email enrol — comma separated | Logged in | Enter comma-separated emails | Same result as newline | Unit |
| SCH-39 | Non-email strings filtered out | Logged in | Enter mixed valid/invalid strings | Only valid emails (containing @) sent to API | Unit |
| SCH-40 | Live email count shown | Logged in | Type in email textarea | Counter below textarea updates in real time | — |

---

### 3.17 Teacher Management (`/school/teachers`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| SCH-41 | Invite form visible for school_admin | Logged in as school_admin | Navigate to `/school/teachers` | Name and email fields + Send invitation button | — |
| SCH-42 | Access denied for non-admin teacher | Logged in as teacher | Navigate to `/school/teachers` | Access-denied message shown (no redirect) | — |
| SCH-43 | Successful invite adds to list | school_admin | Fill form; click Send invitation | Invited teacher appears in table | Unit |
| SCH-44 | Teachers nav item hidden for non-admin | Logged in as teacher | View sidebar | "Teachers" nav item not visible | — |

---

### 3.18 School Settings (`/school/settings`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| SCH-45 | School profile details render | Logged in | Navigate to `/school/settings` | School name, email, country, status, ID visible | — |
| SCH-46 | Enrolment code displayed and copyable | Logged in | View settings | Code in monospace font; Copy button works | — |
| SCH-47 | Billing portal button visible for admin | Logged in as school_admin | View settings | "Open billing portal" button visible | — |
| SCH-48 | Billing button hidden for non-admin | Logged in as teacher | View settings | Billing section not visible; contact admin message shown | — |

---

## 4. Admin Console

> **Auth note:** Admin portal uses client-side localStorage (`sb_admin_token`). No Auth0 required. Missing token → redirected to `/admin/login` via `useEffect`.

### 4.1 Admin Login (`/admin/login`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| ADM-01 | Login form renders | None | Navigate to `/admin/login` | Email field, password field, Sign in button visible | E2E |
| ADM-02 | Successful login stores token | Valid admin credentials | Enter valid email/pass; click Sign in | `sb_admin_token` set in localStorage; redirects to `/admin/dashboard` | E2E |
| ADM-03 | Failed login shows error message | Invalid credentials | Enter wrong email/pass; click Sign in | Error message "Invalid credentials" visible | E2E |
| ADM-04 | Sign in button disabled during submit | Any | Click Sign in | Button shows "Signing in…"; disabled until response | — |

---

### 4.2 Auth Redirects (Admin)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| ADM-05 | `/admin/dashboard` redirects without token | No `sb_admin_token` | Navigate to `/admin/dashboard` | Redirects to `/admin/login` | E2E |
| ADM-06 | `/admin/analytics` redirects without token | No `sb_admin_token` | Navigate to `/admin/analytics` | Redirects to `/admin/login` | E2E |

---

### 4.3 Admin Dashboard (`/admin/dashboard`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| ADM-07 | Dashboard heading renders | Token set | Navigate to `/admin/dashboard` | "Platform Dashboard" heading visible | E2E |
| ADM-08 | Subscription KPI cards render | Token + backend up | View dashboard | Total Active, MRR, New, Churn cards visible | E2E |
| ADM-09 | Pipeline section renders | Token set | View dashboard | Pipeline summary section visible | E2E |
| ADM-10 | Loading skeletons shown on fetch | Token set | Navigate (slow network) | Skeleton cards visible before data arrives | — |

---

### 4.4 Analytics (`/admin/analytics`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| ADM-11 | Page heading renders | Token set | Navigate to `/admin/analytics` | "Platform Analytics" heading visible | E2E |
| ADM-12 | Subscription table renders | Token + backend up | View analytics | Metrics table with monthly/annual/MRR/churn rows | E2E |
| ADM-13 | Struggle report table renders | Token + backend up | View analytics | Units listed with avg score and fail-rate column | — |
| ADM-14 | High fail-rate highlighted in red | Token + data with >40% fail | View struggle report | Fail rate > 40% shown in red; < 20% in green | — |

---

### 4.5 Pipeline List (`/admin/pipeline`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| ADM-15 | Pipeline page heading renders | Token set | Navigate to `/admin/pipeline` | "Pipeline Jobs" heading visible | E2E |
| ADM-16 | Trigger job button visible | Token set | View page | "Trigger job" link/button visible | E2E |
| ADM-17 | Jobs table renders | Token + jobs exist | View page | Job ID, curriculum, status badge, progress, timestamp | — |
| ADM-18 | Status badges colour-coded | Token + varied statuses | View page | queued=gray, running=blue, done=green, failed=red | — |
| ADM-19 | Clicking job ID navigates to detail | Token + job exists | Click job ID | Navigates to `/admin/pipeline/{job_id}` | — |
| ADM-20 | Page auto-refreshes every 15 s | Token + running job | Wait on page | Job status updates without manual refresh | — |

---

### 4.6 Pipeline Trigger (`/admin/pipeline/trigger`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| ADM-21 | Trigger form renders for product_admin | Token with product_admin role | Navigate to page | Grade dropdown, language input, force checkbox, Trigger button visible | — |
| ADM-22 | Access denied for developer role | Token with developer role | Navigate to trigger page | "Access denied" message; form not shown | — |
| ADM-23 | Successful trigger redirects to job | product_admin + valid form | Fill form; click Trigger Job | Redirects to `/admin/pipeline/{new_job_id}` | — |
| ADM-24 | Error shown on trigger failure | product_admin + backend error | Click Trigger Job | Error alert visible | — |
| ADM-25 | Force checkbox overrides existing content | product_admin | Check "Force regenerate"; trigger | Job created with force=true | — |

---

### 4.7 Pipeline Job Detail (`/admin/pipeline/[job_id]`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| ADM-26 | Progress bar renders while running | Token + running job | Navigate to job detail | Blue progress bar with percentage | — |
| ADM-27 | Progress bar turns green when done | Token + completed job | Navigate to job detail | Green bar at 100% + CheckCircle icon | — |
| ADM-28 | Failed state shows red + failure count | Token + failed job | Navigate to job detail | Red indicator + "N units failed" warning | — |
| ADM-29 | Built/Total/Failed counts visible | Token + any job | View page | Three stat boxes with numbers | — |
| ADM-30 | Back link returns to pipeline list | Token | Click "Back to pipeline" | Navigates to `/admin/pipeline` | — |

---

### 4.8 Content Review Queue (`/admin/content-review`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| ADM-31 | Review queue page renders | Token set | Navigate to `/admin/content-review` | "Content Review Queue" heading visible | E2E |
| ADM-32 | Status filter tabs render | Token set | View page | pending / approved / published / rejected / blocked tabs visible | E2E |
| ADM-33 | Filtering by status updates list | Token + backend up | Click "approved" tab | Only approved items shown | — |
| ADM-34 | Review link navigates to detail | Token + items exist | Click "Review →" on an item | Navigates to `/admin/content-review/{version_id}` | — |
| ADM-35 | Empty state when no items | Token + empty queue | View page | "No pending items" message | — |

---

### 4.9 Content Review Detail (`/admin/content-review/[version_id]`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| ADM-36 | Lesson preview renders | Token + item exists | Navigate to detail | Unit title, metadata, lesson text preview visible | — |
| ADM-37 | Approve button visible for pending | Token + pending item | View page | "Approve" button visible | — |
| ADM-38 | Reject opens reason modal | Token + pending item | Click "Reject" | Modal with reason textarea appears | — |
| ADM-39 | Reject requires non-empty reason | Token + pending item | Open reject modal; leave empty; click Confirm | Confirm button disabled until reason entered | — |
| ADM-40 | Approve action calls API | Token + pending item | Click Approve | `POST /admin/content-review/{id}/approve` called; redirects to queue | Unit |
| ADM-41 | Reject action calls API with reason | Token + pending item | Reject with reason | `POST .../reject` called with reason body | Unit |
| ADM-42 | Publish button visible for approved (product_admin) | product_admin + approved item | View page | "Publish" button visible | — |
| ADM-43 | Publish action calls API | product_admin + approved | Click Publish | `POST .../publish` called | Unit |
| ADM-44 | Rollback button visible for published | product_admin + published item | View page | "Rollback" button visible | — |
| ADM-45 | Block opens reason modal | product_admin + published item | Click Block | Modal with reason textarea appears | — |
| ADM-46 | Rollback action calls API | product_admin + published | Click Rollback | `POST .../rollback` called | Unit |
| ADM-47 | Block action calls API with reason | product_admin + published | Block with reason | `POST .../block` called with reason | Unit |
| ADM-48 | Annotations rendered | Token + item has annotations | View detail page | Yellow annotation boxes with reviewer note + timestamp | — |
| ADM-49 | Back link returns to queue | Token | Click "Back to queue" | Navigates to `/admin/content-review` | — |

---

### 4.10 Feedback Queue (`/admin/feedback`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| ADM-50 | Feedback page renders for product_admin | Token with product_admin | Navigate to `/admin/feedback` | Feedback list with star ratings visible | — |
| ADM-51 | Access denied for developer | Token with developer role | Navigate to feedback | "Access denied" message | — |
| ADM-52 | Open/Resolved toggle filters list | product_admin | Click "Resolved" tab | Only resolved feedback shown | — |
| ADM-53 | Resolve action removes item | product_admin + open feedback | Click "Resolve" on an item | Item disappears from open list | — |
| ADM-54 | Pagination works | product_admin + >20 items | Click "Next" | Next page of feedback loaded | — |

---

### 4.11 System Health (`/admin/health`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| ADM-55 | Health page heading renders | Token set | Navigate to `/admin/health` | "System Health" heading visible | E2E |
| ADM-56 | PostgreSQL service row renders | Token set | View page | "PostgreSQL" row with status badge visible | E2E |
| ADM-57 | Redis service row renders | Token set | View page | "Redis" row with status badge visible | E2E |
| ADM-58 | All-ok banner shows green | Token + backend healthy | View page | Green banner "All systems operational" | Unit |
| ADM-59 | Degraded banner shows red | Token + DB down | View page | Red banner "One or more systems degraded" | Unit |
| ADM-60 | Last-checked timestamp updates | Token | Wait 10 s on page | Timestamp refreshes automatically | — |
| ADM-61 | Page always polls (no stop condition) | Token + any state | Wait 30 s | Repeated GET /health calls observed in network tab | Unit |

---

### 4.12 Audit Log (`/admin/audit`)

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| ADM-62 | Audit log renders for product_admin | Token with product_admin | Navigate to `/admin/audit` | Table with timestamp, actor, action, resource | — |
| ADM-63 | Access denied for developer | Token with developer | Navigate to audit | "Access denied" message | — |
| ADM-64 | Action filter narrows results | product_admin + entries | Enter "publish" in filter input | Only publish actions shown | — |
| ADM-65 | Pagination works | product_admin + >50 entries | Click "Next" | Next page loads | — |

---

### 4.13 RBAC — Sidebar Filtering

| TC-ID | Test Case | Precondition | Steps | Expected Result | Auto |
|---|---|---|---|---|---|
| ADM-66 | developer role hides Feedback in nav | Token with developer role | Log in; view sidebar | "Feedback" nav item not visible | E2E |
| ADM-67 | developer role hides Audit Log in nav | Token with developer role | Log in; view sidebar | "Audit Log" nav item not visible | — |
| ADM-68 | super_admin sees all nav items | Token with super_admin | Log in; view sidebar | All 7 nav items visible including Feedback and Audit Log | E2E |
| ADM-69 | product_admin sees Feedback and Audit Log | Token with product_admin | Log in; view sidebar | Feedback and Audit Log visible | — |
| ADM-70 | Sign out clears token | Any admin | Click "Sign out" | `sb_admin_token` removed; redirected to `/admin/login` | — |

---

## 5. Summary

| Portal | Total TCs | Automated (E2E) | Automated (Unit) | Manual Only |
|---|---|---|---|---|
| Public | 28 | 12 | 0 | 16 |
| Student | 47 | 3 | 8 | 36 |
| School | 48 | 2 | 10 | 36 |
| Admin | 70 | 12 | 14 | 44 |
| **Total** | **193** | **29** | **32** | **132** |

> **Next steps to consider:** The 132 manual-only test cases are candidates for automation. Priority areas are the Student learning flow (STU-19 → STU-25 quiz flow) and the School curriculum pipeline (SCH-26 → SCH-34) since these are the core product differentiators.
