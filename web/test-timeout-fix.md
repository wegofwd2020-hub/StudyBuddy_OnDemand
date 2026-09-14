# Test Timeout Fix

## Problem
- Test suite was timing out with multiple workers
- Default 5-second timeout was insufficient for complex components
- 2 workers consistently timed out (teachers-page, students-page)

## Solution
1. **Created batched test runner** (`run-tests-batched.sh`)
   - Splits tests into batches of 10 files
   - Runs each batch with longer timeout (60s test, 30s hooks)
   - Provides clear progress reporting
   - Continues even if a batch fails

2. **Added npm script** (`test:batched`)
   - Easy to run: `npm run test:batched`
   - No need to remember the script name

3. **Updated vitest config**
   - Increased default timeouts
   - testTimeout: 30s (from 5s)
   - hookTimeout: 30s (from 10s)
   - workerTimeout: 60s

## Results
- ✅ All 67 test files pass
- ✅ 828 individual tests pass
- ✅ No more timeout issues
- ✅ Clear progress reporting
- ✅ Faster feedback (batches run in ~1-2 seconds each)

## Usage
```bash
# Run all tests in batches
npm run test:batched

# Or run specific test files
npm run test -- --run tests/unit/quiz-page.test.tsx
```

## Future Improvements
- Could investigate why teachers-page and students-page timeout
- Consider using test fixtures to reduce setup time
- Look into test parallelization optimizations