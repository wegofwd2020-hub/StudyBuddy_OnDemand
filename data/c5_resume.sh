#!/bin/bash
# Resume the Epic 11 C-5 build chain after the 2026-04-22 container restart.
# Runs detached via: docker compose exec -dT celery-pipeline bash /data/c5_resume.sh
set -u

LOG=/data/c5_chain.log

echo "=== [$(date -u +%FT%TZ)] RESUME START (detached) ===" >>"$LOG"

echo "=== [$(date -u +%H:%M:%S)] BUILD 1/2: G12 Science (resume; skips already-built units) ===" >>"$LOG"
python /app/pipeline/build_grade.py --grade 12 --stream science --lang en >>"$LOG" 2>&1

echo "" >>"$LOG"
echo "=== [$(date -u +%H:%M:%S)] BUILD 2/2: G11 Science --force regen (C-5 formatting pass) ===" >>"$LOG"
python /app/pipeline/build_grade.py --grade 11 --stream science --lang en --force >>"$LOG" 2>&1

echo "" >>"$LOG"
echo "=== [$(date -u +%FT%TZ)] RESUME COMPLETE ===" >>"$LOG"
