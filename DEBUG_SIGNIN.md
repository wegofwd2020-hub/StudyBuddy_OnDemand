# Debugging Signin Form Submission Issue

## Problem
The signin form "Sign In" button appears disabled or form submission doesn't send API requests to the backend.

## Solution: Automated Log Capture

We've created a script that automatically opens the signin page, fills in credentials, clicks the button, and captures all browser console logs and network activity.

---

## Quick Start

### Option 1: Run with defaults (local dev environment)

```bash
cd StudyBuddy_OnDemand
chmod +x scripts/run-signin-debug.sh
./scripts/run-signin-debug.sh
```

**Expected output:** Console logs + captured signin-logs-*.json file

---

### Option 2: Run against demo server

```bash
cd StudyBuddy_OnDemand
chmod +x scripts/run-signin-debug.sh
./scripts/run-signin-debug.sh https://demo.usestudybuddy.com/signin student@demo.example.com DemoPass123
```

---

### Option 3: Manual setup (if shell script doesn't work on your OS)

```bash
# 1. Install dependencies (one-time only)
npm install playwright

# 2. Run the capture script
node scripts/capture-signin-logs.js http://localhost/signin student@demo.example.com DemoPass123
```

---

## What the Script Does

1. ✅ Launches a headless Chrome browser
2. ✅ Navigates to the signin page
3. ✅ Fills in email and password fields
4. ✅ Clicks the "Sign In" button
5. ✅ Captures all console messages
6. ✅ Captures all network requests/responses
7. ✅ Captures any JavaScript errors
8. ✅ Saves everything to `signin-logs-TIMESTAMP.json`

---

## What to Look For

After running, check the console output for these logs:

### ✅ If working correctly, you should see:

```
[LOG] [universalLogin] Starting
[LOG] [universalLogin] baseURL: /api/v1
[LOG] [universalLogin] Calling POST /auth/universal-login
[LOG] [universalLogin] Success: 200
[RESPONSE] 200 http://localhost/api/v1/auth/universal-login
```

### ❌ If form submission fails, you'll see one of these patterns:

**Pattern A: Handler never runs**
```
[No [universalLogin] logs at all]
→ Form submission handler didn't execute
```

**Pattern B: Stops at startup**
```
[LOG] [universalLogin] Starting
[LOG] [universalLogin] baseURL: /api/v1
[No more logs]
→ Error before API call (axios misconfiguration?)
```

**Pattern C: Stops after baseURL**
```
[LOG] [universalLogin] Starting
[LOG] [universalLogin] baseURL: /api/v1
[LOG] [universalLogin] Calling POST...
[No response logs]
→ Request sent but response never captured
```

**Pattern D: Network shows no POST**
```
[No network requests to /auth/universal-login]
→ Axios.post() never fired
```

**Pattern E: Error caught**
```
[ERROR] [universalLogin] Error: [error message here]
→ Exception thrown (see error message for details)
```

---

## How to Share Results

Once you run the script tomorrow, share:

1. **The console output** from the script (copy-paste from terminal)
2. **The JSON file** (signin-logs-*.json)
3. **Which pattern matches** from the section above

Example:

```
📊 Captured Logs Summary
Console messages: 8
Network requests: 2
Errors: 0

🔍 [universalLogin] Logs Found:
  [log] [universalLogin] Starting
  [log] [universalLogin] baseURL: /api/v1
  [log] [universalLogin] Calling POST /auth/universal-login
  [error] [universalLogin] Error: TypeError: axios is undefined
```

---

## Troubleshooting the Script Itself

**Problem: "command not found: npm"**
- Solution: Install Node.js from nodejs.org

**Problem: "Playwright not found"**
- Solution: Run `npm install playwright` first

**Problem: "Port 3000 not accessible" (for localhost testing)**
- Solution: Make sure `docker compose up` is running, or use the demo URL instead

**Problem: Script hangs**
- Solution: It's waiting for the page. Press Ctrl+C and try with a different URL

---

## Files Involved

- `scripts/run-signin-debug.sh` — Shell wrapper (calls the Node script)
- `scripts/capture-signin-logs.js` — Node.js script that captures logs
- `signin-logs-*.json` — Output file with all captured data

---

## Next Steps

1. Run tomorrow: `./scripts/run-signin-debug.sh`
2. Check the console output for patterns
3. Share the output + observations
4. We'll fix the issue based on which pattern matches

---

**Questions?** Check the script output carefully — it will show exactly where the signin flow breaks.
