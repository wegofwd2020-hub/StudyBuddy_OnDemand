# StudyBuddy — Validation Checklist (your 14 Jun 2026 feedback)

Hi Venki — thanks again for the detailed run-through. **Every item from your
`Feedback_06_14_2026.docx` has been fixed and is now live on the demo.** Could
you re-check them when you get a chance and tick off anything that looks good (or
flag anything that still doesn't)?

**Where to test:** https://demo.usestudybuddy.com
**Before you start:** the fixes were just deployed, so please do a **hard refresh**
(Ctrl/Cmd + Shift + R) — or sign out and back in — so your browser picks up the
latest version.

You'll need your **student** demo login for most items, and your **school‑admin**
login for the last one.

---

## 1. Quiz

| # | What you reported | What we changed | How to check | OK? |
|---|---|---|---|---|
| 1 | "Try again" didn't work | The button now restarts the quiz cleanly | Finish a quiz → click **Try Again** → it should reload a fresh attempt | ☐ |
| 2 | Score looked wrong (e.g. 8/5) | Score can no longer exceed the number of questions | Take a quiz; the score reads e.g. **6/8**, never more than the total | ☐ |
| 3 | Show the subject on the Score page | The subject name now appears on the result screen | Finish a quiz → the subject is shown on the score page | ☐ |

## 2. Unit Progress

| # | What you reported | What we changed | How to check | OK? |
|---|---|---|---|---|
| 4 | "Best score 6%" looked wrong | Best score is now a proper percentage | Open **Progress** → Unit Progress → Best score reads a sensible % | ☐ |
| 5 | Subject showed "Unknown" | Subjects now resolve to real names everywhere | Progress / Stats / History show real subjects (Mathematics, Physics…), not "Unknown" | ☐ |
| 6 | "Strongest" showed "Unknown" | Same fix as above | The "Strongest" subject shows a real name | ☐ |
| 7 | Time always showed 0 | Lesson time is now recorded and saved | View a lesson for a bit, then check Unit Progress → **Time** is no longer 0 | ☐ |

## 3. Progress & counts

| # | What you reported | What we changed | How to check | OK? |
|---|---|---|---|---|
| 8 | "Unknown" in lots of places | Subjects resolve across all screens, incl. the chart (see #19) | Spot‑check Progress, Stats, History — no "Unknown" | ☐ |
| 9 | The "6/5" count looked wrong | Same as the score fix (#2) | Counts now read correctly (out of the real total) | ☐ |
| 10 | Attempt #2 count mismatched | Duplicate/phantom attempts removed | History shows one row per real attempt, numbered correctly | ☐ |
| 11 | Show subject name with the code | Subject name now shown alongside the code | Subject appears as the readable name | ☐ |

## 4. My Stats

| # | What you reported | What we changed | How to check | OK? |
|---|---|---|---|---|
| 12 | Stats didn't refresh after a quiz (needed a browser refresh) | Stats refresh automatically | Finish a quiz → go to **My Stats** → numbers update **without** a manual browser refresh | ☐ |
| 19 | Subject Breakdown chart had no names + odd single bar | Chart now uses real subject names and one bar **per subject** | **My Stats** → Subject Breakdown shows separate, labelled bars; the 7d / 30d / All‑time filter now actually changes the chart | ☐ |

## 5. Lessons & content

| # | What you reported | What we changed | How to check | OK? |
|---|---|---|---|---|
| 13 | "Could not load lesson" (Mathematics → Pythagorean Theorem) | Lessons that aren't published yet now show a calm "not available yet" message instead of a scary error — and units without content are blocked from selection (see #14) | Open a lesson; if its content exists it loads, otherwise you see a friendly "not available yet" note (no red error) | ☐ |
| 14 | Don't let users pick subjects/lessons/quizzes with no content | Units without content are now **greyed out** with a "Coming soon" tag and can't be opened | **Subjects** / **Curriculum Map** → units without content are dimmed / "Coming soon" and not clickable | ☐ |
| 18 | "Continue Learning" threw an error | Same fix as #13 | Click **Continue Learning** on the dashboard → it opens the lesson or shows the friendly note, no error | ☐ |
| 15 | Spanish didn't switch the content | Your language choice now applies **immediately** (no logout needed) | **Settings → Language** → pick **Français**, Save → open a lesson → it's in French (for units that have a French version). *See note below about Spanish.* | ☐ |

> **Note on Spanish:** the language **setting** now takes effect right away — that
> was the bug. However, Spanish lesson content hasn't been authored yet, so Spanish
> currently falls back to English (Settings now says this honestly). French content
> exists for some units, which is the best way to confirm the switch works. We can
> schedule Spanish content generation separately if you'd like.

## 6. Navigation

| # | What you reported | What we changed | How to check | OK? |
|---|---|---|---|---|
| 16 | Name change didn't show until re‑login (Charlie → Davis) | The header updates as soon as you save | **Settings** → change your display name → Save → the header updates immediately (no logout) | ☐ |
| 17 | "Subjects" and "Curriculum Map" looked like duplicates | Both pages now state their purpose so the difference is clear | **Subjects** = "Browse every subject and open a lesson or quiz." · **Curriculum Map** = "Track your progress through the year, unit by unit." (with progress badges) | ☐ |

## 7. School Admin

| # | What you reported | What we changed | How to check | OK? |
|---|---|---|---|---|
| 20 | Pass Rate (1st attempt) + Quiz Attempts count looked off | Pass Rate can no longer exceed 100%; attempt counting corrected | Sign in as **school‑admin** → Dashboard → Pass Rate is a sensible % (≤ 100) and Quiz Attempts looks right | ☐ |

---

### Anything still off?

If any row doesn't behave as described, just reply with the **#** and a quick
screenshot — that maps straight back to our tracking so we can jump on it.

Thanks!
