#!/bin/bash

# Run tests in batches to avoid timeout issues

set -e

echo "🧪 Running tests in batches to avoid timeouts..."

# Count total test files
TOTAL_FILES=$(find tests/unit -name "*.test.ts" -o -name "*.test.tsx" | wc -l)
echo "📊 Total test files: $TOTAL_FILES"

# Create array of all test files
TEST_FILES=($(find tests/unit -name "*.test.ts" -o -name "*.test.tsx" | sort))

# Batch size (run 10 files at a time)
BATCH_SIZE=10
PASSED=0
FAILED=0

# Function to run a batch of tests
run_batch() {
    local batch=("$@")
    echo "🚀 Running batch of ${#batch[@]} files..."

    # Join files with space for npm command
    local files_str=$(printf "%s " "${batch[@]}")

    # Run tests with longer timeout
    if npm run test -- --run --testTimeout=60000 --hookTimeout=30000 $files_str; then
        PASSED=$((PASSED + ${#batch[@]}))
        echo "✅ Batch passed (${#batch[@]} files)"
        return 0
    else
        FAILED=$((FAILED + ${#batch[@]}))
        echo "❌ Batch failed (${#batch[@]} files)"
        return 1
    fi
}

# Run tests in batches
for ((i=0; i<${#TEST_FILES[@]}; i+=BATCH_SIZE)); do
    batch=("${TEST_FILES[@]:i:BATCH_SIZE}")
    echo "📦 Batch $((i/BATCH_SIZE + 1))/$((${#TEST_FILES[@]}/BATCH_SIZE + 1))"

    if ! run_batch "${batch[@]}"; then
        echo "⚠️  Batch failed but continuing with next batch..."
    fi

    echo "---"
done

echo ""
echo "📊 Test Summary:"
echo "✅ Passed: $PASSED files"
echo "❌ Failed: $FAILED files"
echo "📈 Total: $((PASSED + FAILED)) files"

if [ $FAILED -eq 0 ]; then
    echo "🎉 All tests passed!"
    exit 0
else
    echo "💥 Some tests failed!"
    exit 1
fi