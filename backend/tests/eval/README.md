# Visual Resolver Eval Set

Eval harness for the StudyBuddy visual library resolver (issue #323).

## What this is for

The pipeline resolver runs in two stages:

1. An LLM reads a tutorial section and extracts `VisualNeed` objects
   `{kind, topic_phrase, keywords, confidence}`.
2. The resolver embeds `topic_phrase + " " + keywords.join(" ")` with
   voyage-3-lite (512-dim) and runs a cosine-similarity query against
   `visual_library_entries`, scoped to
   `subject = $section_subject AND archived_at IS NULL`. Distance ≤ 0.85
   counts as a hit.

This eval set drives a CI gate that fails when **precision @ k=1 < 0.70**.
The phase-4 runner (not yet built) will read each record, run
`identify_visual_needs` + `resolve` against the live library, and compare
to `expected_hit` / `expected_entry_id`.

The library has 30 entries across two subjects (math, physics) — sourced
from `scripts/seed_library_sidecars.ts`. Use that file as the canonical
list of valid `expected_entry_id` values.

## How to run the eval

Phase 4 (not yet built):

```bash
bun scripts/run_resolver_eval.ts \
  --input backend/tests/eval/visual_resolver_eval.jsonl \
  --gate precision_at_1=0.70
```

Until the runner exists, you can lint the JSONL by hand:

```bash
python3 -c "
import json
for i, line in enumerate(open('backend/tests/eval/visual_resolver_eval.jsonl'), 1):
    json.loads(line)  # raises on malformed lines
print('ok')
"
```

## Distribution

50 records total, split in this exact order:

| Lines  | Block             | Count |
|--------|-------------------|-------|
| 1–10   | known_positive    | 10    |
| 11–20  | known_negative    | 10    |
| 21–50  | borderline*       | 30    |

Borderline-block subdistribution:

| Category                       | Count | Hit/Miss |
|--------------------------------|-------|----------|
| borderline_synonym             | 8     | 8 hits   |
| borderline_multi_need          | 2     | 2 hits   |
| borderline_adjacent_topic      | 12    | 12 misses |
| borderline_subject_mismatch    | 4     | 4 misses  |
| no_visual_need                 | 4     | 4 misses  |

Net borderline split: 10 hits / 20 misses (matches the spec).

## Schema

One JSON object per line. No array wrapper, no trailing comma.

| Field               | Type    | Required | Notes |
|---------------------|---------|----------|-------|
| `id`                | string  | yes      | `eval-001` … `eval-050`, zero-padded |
| `category`          | enum    | yes      | see closed enum below |
| `section_content`   | string  | yes      | 50–200 words; Grade-11 tutorial prose |
| `section_title`     | string  | yes      | 2–6 words |
| `subject`           | enum    | yes      | see closed enum below |
| `expected_hit`      | bool    | yes      | true = resolver should return a hit at k=1 |
| `expected_entry_id` | string  | iff hit  | must match an `id` in `scripts/seed_library_sidecars.ts` |
| `rationale`         | string  | yes      | 8–20 words explaining the expected outcome |

### Closed enums

`category` ∈ {
  `known_positive`,
  `known_negative`,
  `borderline_subject_mismatch`,
  `borderline_adjacent_topic`,
  `borderline_synonym`,
  `borderline_multi_need`,
  `no_visual_need`
}

`subject` ∈ {
  `physics`, `chemistry`, `math`, `biology`,
  `geography`, `history`, `languages`
}

The library only has math + physics entries today, so `expected_hit: true`
records must use `subject ∈ {math, physics}`. Records with any other
subject can never match by SQL filter.

## How to add new records

1. Read `scripts/seed_library_sidecars.ts` to see what library entries
   exist. The `SPECS` array is the authoritative list.
2. Pick a category from the closed enum.
3. Write `section_content` in 50–200 words of Grade-11 tutorial prose.
   Don't telegraph the answer by using the entry's `topic_phrase`
   verbatim — describe the concept the way a textbook explainer would.
4. If `expected_hit: true`, set `expected_entry_id` to a valid library
   id and confirm the section's `subject` is the same as that entry's
   subject. If `expected_hit: false`, omit `expected_entry_id`.
5. Append the record at the bottom (give it the next sequential id).
   Keep the block ordering in mind — known_positive lines 1–10,
   known_negative lines 11–20, borderline 21–N. Re-balance counts in
   this README if your additions skew the distribution.
6. Validate before commit:

   ```bash
   wc -l backend/tests/eval/visual_resolver_eval.jsonl
   python3 -c "import json; [json.loads(l) for l in open('backend/tests/eval/visual_resolver_eval.jsonl')]"
   ```

## Sample record

```json
{
  "id": "eval-001",
  "category": "known_positive",
  "section_content": "When a ball leaves the hand at an angle to the ground, two things happen at once. Horizontally it just keeps gliding at whatever sideways speed it started with, because no force pushes it forward or backward. Vertically it slows down, stops for an instant, and then falls back under gravity at 9.8 m/s². Combine the two and the path you trace out is a parabola.",
  "section_title": "Throwing a Ball at an Angle",
  "subject": "physics",
  "expected_hit": true,
  "expected_entry_id": "physics-kinematics-projectile-trajectory",
  "rationale": "Section is about projectile flight at an angle; library has a 60-degree trajectory diagram."
}
```
