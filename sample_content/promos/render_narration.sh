#!/bin/bash
# render_narration.sh — split a narration.ssml file into per-slide MP3s
# rendered via AWS Polly neural voices.
#
# Usage:
#   ./render_narration.sh teacher-story Joanna
#   ./render_narration.sh student-story Salli
#
# Pre-reqs:
#   - AWS CLI configured with Polly access (us-east-1)
#   - jq, awk
#   - The file sample_content/promos/${STORY}/audio/narration.ssml exists

set -euo pipefail

STORY="${1:?usage: $0 <story-dir> <polly-voice>}"
VOICE="${2:?usage: $0 <story-dir> <polly-voice>}"

ROOT="$(cd "$(dirname "$0")" && pwd)"
SRC="${ROOT}/${STORY}/audio/narration.ssml"
OUT_DIR="${ROOT}/${STORY}/Option3_Video/public/audio"

if [ ! -f "$SRC" ]; then
  echo "narration source not found: $SRC" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"

# Extract each <speak>...</speak> block. The comment line above each block
# names the output file (e.g. "<!-- slide-01.mp3 -->"). awk pulls them as
# (filename, ssml) tuples and writes to a tmp work dir.
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

awk -v work="$WORK" '
  /<!-- slide-/ {
    match($0, /slide-[0-9]+\.mp3/)
    fname = substr($0, RSTART, RLENGTH)
    next
  }
  /<speak>/ { capturing = 1 }
  capturing { buf = buf $0 ORS }
  /<\/speak>/ {
    if (fname == "") { print "ERROR: <speak> block with no slide filename" > "/dev/stderr"; exit 1 }
    out = work "/" fname ".ssml"
    printf "%s", buf > out
    close(out)
    fname = ""; buf = ""; capturing = 0
  }
' "$SRC"

count=0
for ssml in "$WORK"/*.ssml; do
  [ -e "$ssml" ] || continue
  fname="$(basename "$ssml" .ssml)"
  echo "render: $fname (voice=$VOICE)"
  aws polly synthesize-speech \
    --engine neural \
    --voice-id "$VOICE" \
    --text-type ssml \
    --text "file://$ssml" \
    --output-format mp3 \
    "$OUT_DIR/$fname" \
    > /dev/null
  count=$((count + 1))
done

echo "rendered $count clips into $OUT_DIR"
