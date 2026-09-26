#!/bin/bash
# =============================================================================
# scripts/demo/backup-all-grades-content.sh — backup all grades (8-12) content
#
# Backs up content for grades 8-12 into organized structure:
#   backups/<YYYY-mm-dd_HH-MM>/grade_8/
#   backups/<YYYY-mm-dd_HH-MM>/grade_9/
#   ...
#
# Usage:
#   bash scripts/demo/backup-all-grades-content.sh
#
# Output: backups/<YYYY-mm-dd_HH-MM>/grade_{8,9,10,11,12}/
# =============================================================================

set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-.}"
CONTENT_STORE="${CONTENT_STORE:-$INSTALL_DIR/content_store_data}"
BACKUP_BASE_DIR="${BACKUP_BASE_DIR:-$INSTALL_DIR/backups}"

# Timestamp for this backup run (used for directory grouping)
TIMESTAMP=$(date -u +'%Y-%m-%d_%H-%M')
BACKUP_RUN_DIR="$BACKUP_BASE_DIR/$TIMESTAMP"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }
log_err() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] ERROR: $*" >&2; }

# Get version information
get_app_version() {
  grep "^__version__" "$INSTALL_DIR/backend/main.py" 2>/dev/null | cut -d'"' -f2 || echo "unknown"
}

get_app_commit() {
  git -C "$INSTALL_DIR" rev-parse --short HEAD 2>/dev/null || echo "unknown"
}

get_db_schema_version() {
  docker compose -f "$INSTALL_DIR/docker-compose.yml" exec -T db psql -U studybuddy -d studybuddy -c "SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 1;" 2>/dev/null | tail -1 | tr -d ' ' || echo "unknown"
}

export_db_schema_for_grade() {
  local grade=$1
  local output_file=$2
  # Use a SQL dump file instead; just export rows for this grade using psql COPY command
  docker compose -f "$INSTALL_DIR/docker-compose.yml" exec -T db psql -U studybuddy -d studybuddy << EOSQL > "$output_file" 2>/dev/null
\copy (SELECT * FROM curricula WHERE curriculum_id LIKE 'default-2026-g${grade}%') TO STDOUT
\copy (SELECT * FROM curriculum_units WHERE curriculum_id LIKE 'default-2026-g${grade}%') TO STDOUT
EOSQL
}

APP_VERSION=$(get_app_version)
APP_COMMIT=$(get_app_commit)
DB_SCHEMA_VERSION=$(get_db_schema_version)

log "Starting backup of all grades (8-12)"
log "Backup directory: $BACKUP_RUN_DIR"
log "App version: $APP_VERSION (commit: $APP_COMMIT)"
log "DB schema version: $DB_SCHEMA_VERSION"
log ""

mkdir -p "$BACKUP_RUN_DIR"

# Write global backup metadata
cat > "$BACKUP_RUN_DIR/metadata.json" << EOF
{
  "timestamp": "$TIMESTAMP",
  "backup_version": "1.0",
  "app_version": "$APP_VERSION",
  "app_commit": "$APP_COMMIT",
  "db_schema_version": "$DB_SCHEMA_VERSION",
  "content_structure_version": 2,
  "created_at": "$(date -u +'%Y-%m-%dT%H:%M:%SZ')",
  "notes": "Full backup of all grades"
}
EOF
log "Wrote backup metadata: $BACKUP_RUN_DIR/metadata.json"

TOTAL_SIZE=0
FAILED_GRADES=()

# Backup each grade
for grade in 8 9 10 11 12; do
  GRADE_DIR="$BACKUP_RUN_DIR/grade_$grade"
  mkdir -p "$GRADE_DIR"

  log "Backing up Grade $grade..."

  # Find all curriculum directories for this grade
  G_DIRS=$(find "$CONTENT_STORE/curricula" -maxdepth 1 -type d -name "default-2026-g${grade}*" 2>/dev/null || true)

  if [[ -z "$G_DIRS" ]]; then
    log "  WARNING: no content found for grade $grade"
    FAILED_GRADES+=("$grade")
    continue
  fi

  # Create tarball for this grade
  TARBALL="$GRADE_DIR/content.tar.gz"
  DB_EXPORT="$GRADE_DIR/schema.sql"

  if tar -czf "$TARBALL" -C "$CONTENT_STORE/curricula" $(echo "$G_DIRS" | xargs basename -a) 2>/dev/null; then
    SIZE=$(du -h "$TARBALL" | cut -f1)
    TOTAL_SIZE=$((TOTAL_SIZE + $(du -b "$TARBALL" | cut -f1)))
    SHA=$(sha256sum "$TARBALL" | awk '{print $1}')

    # Export database schema for this grade
    log "  Exporting DB schema for Grade $grade..."
    export_db_schema_for_grade "$grade" "$DB_EXPORT"
    if [[ -f "$DB_EXPORT" ]]; then
      log "  ✅ DB schema exported: $DB_EXPORT"
    fi

    # Get content version from meta.json
    CONTENT_VERSION="unknown"
    CONTENT_SCHEMA_VERSION="2"
    for dir in $G_DIRS; do
      META_FILE="$CONTENT_STORE/curricula/$dir/meta.json"
      if [[ -f "$META_FILE" ]]; then
        CONTENT_VERSION=$(jq -r '.content_version // "unknown"' "$META_FILE" 2>/dev/null || echo "unknown")
        CONTENT_SCHEMA_VERSION=$(jq -r '.schema_version // "2"' "$META_FILE" 2>/dev/null || echo "2")
        break
      fi
    done

    log "  ✅ Grade $grade: $TARBALL ($SIZE)"
    log "     SHA256: $SHA | Content v$CONTENT_VERSION"

    # Write manifest for this grade with version info
    cat > "$GRADE_DIR/manifest.json" << MANIFEST
{
  "grade": $grade,
  "timestamp": "$TIMESTAMP",
  "size_bytes": $(du -b "$TARBALL" | cut -f1),
  "sha256": "$SHA",
  "file": "content.tar.gz",
  "db_schema_file": "schema.sql",
  "db_schema_size_bytes": $([ -f "$DB_EXPORT" ] && du -b "$DB_EXPORT" | cut -f1 || echo 0),
  "content_version": "$CONTENT_VERSION",
  "content_schema_version": "$CONTENT_SCHEMA_VERSION",
  "app_version": "$APP_VERSION",
  "app_commit": "$APP_COMMIT",
  "db_schema_version": "$DB_SCHEMA_VERSION"
}
MANIFEST
  else
    log "  ❌ Grade $grade: tar failed"
    FAILED_GRADES+=("$grade")
  fi
done

log ""
log "═════════════════════════════════════════════════════════════════"
log "Backup Summary"
log "═════════════════════════════════════════════════════════════════"
log "Timestamp: $TIMESTAMP"
log "Total size: $(numfmt --to=iec-i --suffix=B $TOTAL_SIZE 2>/dev/null || echo "$TOTAL_SIZE bytes")"
log ""

if [[ ${#FAILED_GRADES[@]} -eq 0 ]]; then
  log "✅ All grades backed up successfully"
  log ""
  log "Backup structure:"
  find "$BACKUP_RUN_DIR" -type f | sed 's|^|  |'
  exit 0
else
  log "⚠️  Failed grades: ${FAILED_GRADES[*]}"
  exit 1
fi
