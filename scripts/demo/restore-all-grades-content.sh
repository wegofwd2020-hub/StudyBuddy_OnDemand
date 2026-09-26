#!/bin/bash
# =============================================================================
# scripts/demo/restore-all-grades-content.sh — restore all grades from backup
#
# Restores grades 8-12 from backup created by backup-all-grades-content.sh
#
# Usage:
#   bash scripts/demo/restore-all-grades-content.sh <backup-timestamp>
#   bash scripts/demo/restore-all-grades-content.sh 2026-09-26_16-47
#
# Restores from: backups/<backup-timestamp>/grade_{8,9,10,11,12}/
# =============================================================================

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <backup-timestamp>"
  echo ""
  echo "Available backups:"
  ls -d backups/*/  2>/dev/null | sed 's|backups/||g; s|/||g' | sort -r || echo "(none found)"
  exit 1
fi

INSTALL_DIR="${INSTALL_DIR:-.}"
CONTENT_STORE="${CONTENT_STORE:-$INSTALL_DIR/content_store_data}"
BACKUP_BASE_DIR="${BACKUP_BASE_DIR:-$INSTALL_DIR/backups}"

BACKUP_TIMESTAMP="$1"
BACKUP_RUN_DIR="$BACKUP_BASE_DIR/$BACKUP_TIMESTAMP"

if [[ ! -d "$BACKUP_RUN_DIR" ]]; then
  echo "ERROR: backup directory not found: $BACKUP_RUN_DIR"
  exit 1
fi

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }
log_err() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] ERROR: $*" >&2; }

restore_db_schema_for_grade() {
  local grade=$1
  local schema_file=$2
  if [[ ! -f "$schema_file" ]]; then
    log "  WARNING: no schema.sql for Grade $grade"
    return 1
  fi
  log "  Importing DB schema for Grade $grade..."
  # Restore COPY format data using psql
  docker compose -f "$INSTALL_DIR/docker-compose.yml" cp "$schema_file" db:/tmp/grade_${grade}_schema.sql 2>/dev/null || true
  docker compose -f "$INSTALL_DIR/docker-compose.yml" exec -T db psql -U studybuddy -d studybuddy << EOSQL 2>/dev/null
\copy curricula FROM /tmp/grade_${grade}_schema.sql
\copy curriculum_units FROM /tmp/grade_${grade}_schema.sql
EOSQL
  docker compose -f "$INSTALL_DIR/docker-compose.yml" exec -T db rm -f /tmp/grade_${grade}_schema.sql 2>/dev/null || true
  log "  ✅ DB schema imported for Grade $grade"
}

log "Restoring all grades from backup: $BACKUP_TIMESTAMP"
log "Source: $BACKUP_RUN_DIR"
log ""

# Create safety pre-backup before overwriting
SAFETY_BACKUP_DIR="$BACKUP_BASE_DIR/pre-restore-$(date -u +'%Y-%m-%d_%H-%M')"
mkdir -p "$SAFETY_BACKUP_DIR"

log "Creating safety backup of existing content..."
for grade in 8 9 10 11 12; do
  G_DIRS=$(find "$CONTENT_STORE/curricula" -maxdepth 1 -type d -name "default-2026-g${grade}*" 2>/dev/null || true)
  if [[ -n "$G_DIRS" ]]; then
    tar -czf "$SAFETY_BACKUP_DIR/grade_${grade}_prebackup.tar.gz" -C "$CONTENT_STORE/curricula" $(echo "$G_DIRS" | xargs basename -a) 2>/dev/null || true
  fi
done
log "Safety backup created at: $SAFETY_BACKUP_DIR"
log ""

# Interactive confirmation
echo "⚠️  This will restore the following grades:"
for grade_dir in "$BACKUP_RUN_DIR"/grade_*/; do
  if [[ -d "$grade_dir" ]]; then
    GRADE=$(basename "$grade_dir" | sed 's/grade_//')
    SIZE=$(du -sh "$grade_dir" | cut -f1)
    echo "  - Grade $GRADE ($SIZE)"
  fi
done
echo ""
read -p "Continue with restore? (yes/no): " -r confirm
if [[ "$confirm" != "yes" ]]; then
  log "Restore cancelled"
  exit 0
fi

log "Proceeding with restore..."
log ""

FAILED_GRADES=()

# Restore each grade
for grade_dir in "$BACKUP_RUN_DIR"/grade_*/; do
  if [[ ! -d "$grade_dir" ]]; then
    continue
  fi

  GRADE=$(basename "$grade_dir" | sed 's/grade_//')
  TARBALL="$grade_dir/content.tar.gz"
  SCHEMA_FILE="$grade_dir/schema.sql"

  if [[ ! -f "$TARBALL" ]]; then
    log "WARNING: no tarball found for grade $GRADE"
    continue
  fi

  log "Restoring Grade $GRADE..."

  # Delete existing content for this grade
  G_DIRS=$(find "$CONTENT_STORE/curricula" -maxdepth 1 -type d -name "default-2026-g${GRADE}*" 2>/dev/null || true)
  if [[ -n "$G_DIRS" ]]; then
    log "  Removing existing Grade $GRADE content"
    for dir in $G_DIRS; do
      rm -rf "$dir"
    done
  fi

  # Delete existing DB schema for this grade
  log "  Cleaning DB for Grade $GRADE..."
  docker compose -f "$INSTALL_DIR/docker-compose.yml" exec -T db psql -U studybuddy -d studybuddy -c "
    DELETE FROM curriculum_units WHERE curriculum_id LIKE 'default-2026-g${GRADE}%';
    DELETE FROM curricula WHERE curriculum_id LIKE 'default-2026-g${GRADE}%';
  " 2>/dev/null || true

  # Extract tarball
  if tar -xzf "$TARBALL" -C "$CONTENT_STORE/curricula" 2>/dev/null; then
    log "  ✅ Grade $GRADE content restored"
  else
    log "  ❌ Grade $GRADE: tar extraction failed"
    FAILED_GRADES+=("$GRADE")
    continue
  fi

  # Restore DB schema
  if restore_db_schema_for_grade "$GRADE" "$SCHEMA_FILE"; then
    log "  ✅ Grade $GRADE fully restored (content + schema)"
  else
    log "  ⚠️  Grade $GRADE content restored, but schema import failed"
  fi
done

log ""
log "═════════════════════════════════════════════════════════════════"
log "Restore Summary"
log "═════════════════════════════════════════════════════════════════"

if [[ ${#FAILED_GRADES[@]} -eq 0 ]]; then
  log "✅ All grades restored successfully"
  exit 0
else
  log "⚠️  Failed grades: ${FAILED_GRADES[*]}"
  log ""
  log "Safety backup available at: $SAFETY_BACKUP_DIR"
  exit 1
fi
