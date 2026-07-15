# Retest — Forgot / Reset Password (Feedback #444)

Hi Venki — this is now fixed and deployed to the demo. Could you please retest the
**"Forgot your password?"** flow end‑to‑end and confirm it works for you?

**What was wrong:** school accounts (students/teachers) had no working "Forgot
your password?" — the link led nowhere useful and no reset email arrived.

**What's fixed:** "Forgot your password?" now emails you a secure reset link.
You click it, choose a new password, and sign in — no admin needed.

**Where to test:** https://demo.usestudybuddy.com

---

## Before you start

- **Use one of your own accounts** (so the reset email reaches an inbox you can
  open). Recommended: **`kt.shanvenki@gmail.com`** (your original #444 account).
- **Current password (all demo accounts):** `StudyBuddyDemo2026!`
- You'll choose a **new password during the test** — it must be **at least 12
  characters**. Pick something you'll remember, e.g. `MyNewPass2026!`.
- The reset link is **valid for 1 hour** and **works only once**.

---

## Steps

### 1. (Optional) Confirm you can sign in today
1. Go to https://demo.usestudybuddy.com/signin
2. Sign in with your email + `StudyBuddyDemo2026!`
3. ✅ You should reach your dashboard. Then **sign out**.

### 2. Start the reset
1. Go to the **Sign in** page: https://demo.usestudybuddy.com/signin
2. Click **"Forgot your password?"**
3. ✅ You should land on a **"Reset your password"** page with an **Email address** box.

### 3. Request the reset link
1. Enter your account email (e.g. `kt.shanvenki@gmail.com`)
2. Click **"Send reset link"**
3. ✅ You should see: **"Check your email for a reset link."**

### 4. Open the email
1. Check the inbox for that email address (also check **Spam** / **Promotions**).
2. Look for:
   - **From:** StudyBuddy
   - **Subject:** *StudyBuddy — reset your password*
3. ✅ The email should arrive within a minute or two and contain a **"Reset
   password"** button/link.

### 5. Set a new password
1. Click the **"Reset password"** link in the email.
2. ✅ You should land on a **"Set new password"** page.
3. Enter your **new password** (≥ 12 characters) and confirm it.
4. Click **"Set new password"**.
5. ✅ You should see a **"Password updated!"** confirmation.

### 6. Sign in with the new password
1. Go to https://demo.usestudybuddy.com/signin
2. Sign in with your email + your **new** password.
3. ✅ You should reach your dashboard successfully.

---

## Optional extra checks (nice to confirm)

- **Old password is rejected:** try signing in with `StudyBuddyDemo2026!` after the
  reset — it should **fail** ("Incorrect email or password"). ✅
- **Link can't be reused:** click the same reset link from the email a second time —
  it should say the link is **invalid or expired**. ✅

---

## When you're done

- If you'd like to put the account back to the shared demo password, just run the
  reset flow once more and set it to `StudyBuddyDemo2026!`. (Optional.)

## What to report back

For each step, please note **✅ worked** or **❌ problem** (with a screenshot if it
failed). In particular:

1. Did the **"Forgot your password?"** link take you to the reset page?
2. Did the **email arrive**, and how long did it take?
3. Did **setting a new password** succeed?
4. Could you **sign in with the new password**?

Thanks!
