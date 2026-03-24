# My AI Persona & Rules

## Project Context
- Developing a STEM Learning App (Android/Chrome) for students, Grades 5–12.
- Developing an Accessibility AI for PSA Emergency Notifications.

---

## Content Rules

1. **Safety:** All content must be age-appropriate. No violence, profanity, or suggestive themes.
2. **Ethics:** Use inclusive language. Avoid gender-coded roles in STEM examples (e.g., use 'the engineer' or 'they'). Do not use gendered emoji to represent professional roles in diagrams.
3. **STEM Clarity:** Use Mermaid.js diagrams for flowcharts. Explain math step-by-step.
4. **Reading Level:** AI-generated lesson content should target 1–2 grade levels below the student's actual grade to ensure comprehension accessibility.
5. **Error Messages:** Student-facing error messages must be age-appropriate and non-technical. Avoid stack traces, HTTP status codes, or internal identifiers in any message visible to students.
6. **PSA Language:** Emergency notification content must use plain language (Flesch-Kincaid Grade 8 or below), be multi-channel (text + audio + visual), and be compatible with screen readers.

---

## Technical Preferences

- **Primary Language:** Python (backend / pipeline) · Kotlin (Android).
- **Cloud:** No specific cloud platform preference at this time. Architecture decisions should remain cloud-agnostic where possible (e.g., abstract storage behind an interface; avoid vendor-specific SDK lock-in in business logic).
- **Content Moderation:** AlexJS is the current automated content analysis tool (pipeline phase). Azure AI Content Safety and other commercial options are deferred — to be evaluated when AlexJS proves insufficient or when a specific cloud platform is adopted.
- **Compliance:** COPPA and FERPA standards must be considered in all UI/UX and data architecture decisions. See compliance notes below.
- **Async Pattern:** Kotlin Coroutines for all async operations on Android; no callbacks or blocking calls on the main thread.
- **Dependencies:** New dependencies must be reviewed for known CVEs before inclusion. Prefer Azure SDK or well-maintained open-source libraries.

---

## Compliance Notes

### COPPA (Children's Online Privacy Protection Act)
- Applies to students under 13 in US distribution.
- Require verifiable parental consent before collecting any data from under-13 students.
- Collect only minimum necessary PII: name, email, grade, locale.
- No tracking, location data, or behavioural fingerprinting of minors.

### FERPA (Family Educational Rights and Privacy Act)
- Applies to educational records of students at schools receiving US federal funding.
- Parents (or eligible students aged 18+) have the right to inspect and review educational records.
- Schools must obtain written consent before disclosing student educational records to third parties.
- "Directory information" (name, grade level, enrolment status) may be shared without consent unless the school has opted out — but our product should default to not sharing without explicit consent.
- Student progress records, quiz scores, and lesson-view history are educational records under FERPA.
- Implication for architecture: admin and teacher endpoints that expose student records must be scoped to the student's own institution and require teacher/school_admin JWT.

---

## Accessibility Standards

- UI (mobile and web) must target **WCAG 2.1 Level AA**.
- Minimum color contrast ratio: 4.5:1 for normal text, 3:1 for large text.
- All interactive elements must have accessible labels (content descriptions on Android, aria-labels on web).
- Audio content must have text alternatives.
- PSA Notification AI: must support screen readers (TalkBack on Android, VoiceOver on iOS) and high-contrast mode.

---

## Data & Privacy Rules

- **No real student PII in dev or test environments.** Use synthetic data generators. CI must never connect to production databases.
- **Data minimisation:** Collect only name, email, grade, locale. No device ID, location, or behavioural fingerprinting.
- **Retention:** Progress records retained for the lifetime of the account, then anonymised (strip `student_id`) after deletion — 30-day GDPR schedule.
- **AI-generated content is never the output of the student.** Do not attribute AI content to the student or store it as their work product.
