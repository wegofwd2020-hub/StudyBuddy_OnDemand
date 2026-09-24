# StudyBuddy QA Testing Guide — 7 Fixes Deployed

**Date:** September 21, 2026  
**Status:** All fixes merged to `main` and deployed to demo.usestudybuddy.com  
**Tester:** Venki  

---

## Overview

Seven enhancement items have been fixed and deployed to the demo environment. This guide provides step-by-step testing instructions for each fix.

**Test environment:** https://demo.usestudybuddy.com

---

## Quick Setup

1. Log in to demo with admin account (StudyBuddyDemo2026!)
2. Use teacher account: callmds@usestudybuddy.com or kt.shanvenki@usestudybuddy.com
3. Navigate to Reports → Engagement Report for most fixes

---

## Fix #824 — Subject Naming (Reports Display)

**Enhancement ID:** EH-001  
**Issue:** Stream codes (e.g., `default-2026-g11-commerce`) were leaking into subject fallback display  
**Fix:** Filter stream codes in subject name resolution  

### Testing Steps

1. Go to **Reports** → **Engagement Report**
2. Check **Subject** column in unit list
3. **Expected:** Only shows "STEM", "Commerce", "Humanities", "Science"
4. **NOT expected:** Should NOT see `default-2026-g11-commerce` or similar codes

**Pass:** All subjects display clean names  
**Fail:** Any stream codes visible in subject names

---

## Fix #825 — Term Period Calculation (Reports Metrics)

**Enhancement ID:** EH-003  
**Issue:** "This term" metrics were lower than "Last 30 days" (logically impossible)  
**Root cause:** Term period used Sept 1 of last year instead of current academic year  
**Fix:** Correct academic year boundary (Sept 1 current year if month >= 9, else Sept 1 previous year)  

### Testing Steps

1. Go to **Reports** → **Engagement Report**
2. Look at the period selector (top-right, dropdown showing "Last 30 days" / "This term" / etc.)
3. Compare metrics:
   - Click **"Last 30 days"** → note lessons viewed, quiz attempts, pass rate
   - Click **"This term"** → note same metrics
4. **Expected:** This term >= Last 30 days (term should include or equal the 30-day window)
5. **NOT expected:** This term should NOT be lower

**Example:**
- Last 30 days: Lessons 140, Pass rate 65%, Quiz attempts 42
- This term: Should be >= Lessons 140, >= 65% pass rate, >= 42 attempts

**Pass:** Term metrics >= 30d metrics  
**Fail:** Term metrics < 30d metrics

---

## Fix #826 — Score Decimal Precision (Reports Display)

**Enhancement ID:** EH-003  
**Issue:** Unit performance average scores displayed inconsistent decimals (UI showed 0, Excel showed 1)  
**Fix:** Standardize to 1 decimal place throughout  

### Testing Steps

1. Go to **Reports** → **Unit Performance**
2. Look at **Avg Score %** column
3. **Expected:** All scores show 1 decimal place (e.g., 65.2%, 78.5%, 92.1%)
4. **NOT expected:** Scores should NOT show 0 decimals (e.g., 65%, 79%)
5. (Optional) Export to Excel → scores should match UI display

**Pass:** All avg scores display X.X% format  
**Fail:** Inconsistent decimals (some 0, some 1) or no decimals

---

## Fix #827 — Currency Localization Foundation (Quiz Content)

**Enhancement ID:** EH-002  
**Issue:** Currency hardcoded as USD in quiz prompts; need multi-currency support per school  
**Fix:** Build school localization system (DB schema + service layer)  
**Status:** Backend foundation complete; pipeline update pending  

### Testing Steps

1. **Database check:** School profile now includes `currency_code`, `timezone`, `date_format`
2. **Admin API:** Verify `GET /schools/{school_id}/` includes `localization` object
3. **Expected:** Response includes:
   ```json
   "localization": {
     "currency_code": "USD",
     "timezone": "America/New_York",
     "country_code": "US"
   }
   ```

**Pass:** School localization config present in API  
**Fail:** Localization object missing or incomplete

---

## Fix #821 — Alert Resolution (Post-Quiz)

**Enhancement ID:** EH-003  
**Issue:** Pass-rate alerts not re-evaluated immediately after quiz completion  
**Fix:** Dispatch immediate alert re-evaluation task after quiz end  

### Testing Steps

1. Have a student complete a quiz that would trigger/resolve an alert
2. Go to **Reports** → **Alerts** (admin view)
3. **Expected:** Alert status updates within ~10 seconds of quiz completion
4. **NOT expected:** Should NOT require waiting until next daily scheduled task (15+ min)

**Pass:** Alerts update immediately post-quiz  
**Fail:** Alerts require manual refresh or wait for scheduled task

---

## Fix #822 — Endpoint 404 Response (Override Data Loading)

**Enhancement ID:** EH-001 (Admin)  
**Issue:** GET /schools/{school_id}/content/{curriculum_id}/units returned empty data instead of 404 when curriculum didn't exist  
**Fix:** Add explicit 404 check; raise HTTPException if curriculum not found  

### Testing Steps

1. Go to **Admin Console** → **Content Review**
2. Select a forked curriculum
3. Click **"View Unit Overrides"** or edit link
4. **Expected:** Page loads cleanly with unit list and override data
5. **Expected (error case):** If curriculum deleted or invalid, should see proper 404 error

**Pass:** Override data loads or shows clear error (not silent empty response)  
**Fail:** "Failed to load override data" without error details, or endpoint returns 200 with empty list

---

## Fix #823 — Back Button Navigation (Quiz Review)

**Enhancement ID:** EH-002 (Admin)  
**Issue:** Back button on Quiz Review Answers page showed "Failed to load unit status" error  
**Root cause:** Same as #822 — override endpoint returning empty data  
**Fix:** Same fix as #822 applies; endpoint now raises 404 properly  

### Testing Steps

1. Go to **Admin Console** → **Content Review**
2. Find a reviewed quiz with answers
3. Open **Review Answers** page
4. Click **back button** (browser or page back link)
5. **Expected:** Navigate back cleanly to parent page (quiz list or curriculum)
6. **NOT expected:** Should NOT see "Failed to load unit status" or "Failed to load override data" errors

**Pass:** Back navigation works without errors  
**Fail:** Error message appears or page stuck on Review Answers

---

## Test Checklist

| Fix | Enhancement | Status | Notes |
|-----|-------------|--------|-------|
| #824 | EH-001 (Subject names) | ⬜ | Check Reports subject column |
| #825 | EH-003 (Term period) | ⬜ | Compare term vs 30d metrics |
| #826 | EH-003 (Score precision) | ⬜ | Check unit performance decimals |
| #827 | EH-002 (Currency foundation) | ⬜ | Verify DB/API schema |
| #821 | EH-003 (Alert resolution) | ⬜ | Test post-quiz alert update |
| #822 | EH-001 (Endpoint 404) | ⬜ | Check override data loading |
| #823 | EH-002 (Back button) | ⬜ | Test quiz review navigation |

---

## If You Find Issues

1. **Note the exact steps** to reproduce
2. **Screenshot** if UI error
3. **Check browser console** for error messages (F12 → Console tab)
4. **Report to:** Create new issue referencing the enhancement number and test case

---

## Demo Credentials

**Admin Account:**
- Email: venki.kt@usestudybuddy.com
- Password: StudyBuddyDemo2026!
- Role: Super Admin (full access)

**Teacher Accounts:**
- callmds@usestudybuddy.com (Commerce curriculum)
- kt.shanvenki@usestudybuddy.com (STEM curriculum)
- Password: StudyBuddyDemo2026!

---

## Questions?

Refer to the enhancement list (issues #819–#827) for full context. All fixes are documented in their respective PRs (#832, #835, #836, #830).
