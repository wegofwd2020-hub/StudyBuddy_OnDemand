# Backup & Content Version Tracking

## Overview

Tie together three versioning systems to ensure structural changes are properly handled:

1. **Application Code Version** — Git commit hash, semantic version
2. **Content Version** — Tracked in `meta.json` per curriculum
3. **Database Schema Version** — Alembic migration head

## Directory Structure

```
backups/
  <YYYY-mm-dd_HH-MM>/
    metadata.json           ← global backup metadata
    grade_8/
      content.tar.gz
      manifest.json         ← grade-level metadata
    grade_9/
      ...
```

## Metadata Files

### `backups/<timestamp>/metadata.json`
```json
{
  "timestamp": "2026-09-26_21-07",
  "backup_version": "1.0",
  "app_version": "0.2.0",
  "app_commit": "5720f3c",
  "db_schema_version": 71,
  "db_alembic_head": "5720f3c (feat: update backup/restore...)",
  "content_structure_version": 2,
  "grades_included": [8, 9, 10, 11, 12],
  "total_size_bytes": 46137344,
  "created_at": "2026-09-26T21:07:52Z",
  "compatible_app_versions": ["0.2.0", "0.2.1"],
  "notes": "Full backup of all grades with updated pipeline"
}
```

### `backups/<timestamp>/grade_N/manifest.json`
```json
{
  "grade": 9,
  "timestamp": "2026-09-26_21-07",
  "size_bytes": 7340032,
  "sha256": "7d2a7417d6a527c38bc8a3c303dbf01d39f74749ece728d9ee06c5c4f5b93891",
  "file": "content.tar.gz",
  "curriculum_version": "default-2026-g9:v2",
  "subjects_included": ["G9-ENG", "G9-MATH", "G9-SCIENCE", "G9-TECH"],
  "unit_count": 19,
  "content_schema_version": 2,
  "required_app_version": ">=0.2.0"
}
```

## Version Components

### Application Version
**Source:** `backend/main.py` or package.json

```python
# backend/main.py
__version__ = "0.2.0"
__commit__ = "5720f3c"
__schema_version__ = 71  # alembic current head
```

Exposed at: `GET /api/v1/health/deep` → `version` field

### Content Version
**Source:** `meta.json` in each curriculum unit directory

```json
{
  "generated_at": "2026-09-26T20:50:00Z",
  "model": "claude-sonnet-4-6",
  "content_version": 2,
  "langs_built": ["en", "fr", "es"],
  "schema_version": 2,
  "spend_usd": 45.23
}
```

Tracked by: `curriculum_id` + `content_version`

### Database Schema Version
**Source:** Alembic migrations

```bash
# Get current schema version
alembic current
# Output: 5720f3c

# Get version history
alembic history
```

## Migration Tracking

### New Table: `backup_versions`
```sql
CREATE TABLE backup_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  backup_timestamp TEXT NOT NULL,
  app_version TEXT NOT NULL,
  app_commit TEXT NOT NULL,
  db_schema_version INT NOT NULL,
  content_structure_version INT NOT NULL,
  restored_at TIMESTAMPTZ,
  restored_by TEXT,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_backup_timestamp ON backup_versions(backup_timestamp);
CREATE INDEX idx_content_version ON backup_versions(content_structure_version);
```

### New Table: `migration_log`
```sql
CREATE TABLE migration_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  migration_name TEXT NOT NULL,
  from_version INT NOT NULL,
  to_version INT NOT NULL,
  status TEXT CHECK (status IN ('pending', 'running', 'completed', 'failed')),
  error_message TEXT,
  executed_at TIMESTAMPTZ,
  executed_by TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_status ON migration_log(status);
```

## Workflow: Backup

**When backing up:**
1. Read app version from `backend/main.py` or `/health/deep`
2. Get current DB schema version from `alembic current`
3. Read content versions from each curriculum's `meta.json`
4. Write `metadata.json` to backup root with all versions
5. Write `manifest.json` to each grade directory
6. Store backup timestamp in DB (insert `backup_versions` row)

```bash
# Example: during backup
APP_VERSION=$(grep "__version__" backend/main.py | cut -d'"' -f2)
DB_VERSION=$(docker compose exec db alembic current | tail -1)
CONTENT_VERSION=$(jq -r '.content_version' content_store_data/curricula/default-2026-g9/meta.json)

# Write to metadata.json
jq -n \
  --arg timestamp "$TIMESTAMP" \
  --arg app_version "$APP_VERSION" \
  --arg db_version "$DB_VERSION" \
  --arg content_version "$CONTENT_VERSION" \
  '{
    timestamp: $timestamp,
    app_version: $app_version,
    db_schema_version: ($db_version | tonumber),
    content_structure_version: ($content_version | tonumber)
  }' > "$BACKUP_RUN_DIR/metadata.json"
```

## Workflow: Restore

**When restoring:**
1. Read `metadata.json` from backup
2. Check if current app version is compatible
3. Check if current DB schema version matches or has migration path
4. Check content structure version compatibility
5. Run any required migrations
6. Log restore action to `migration_log`
7. Insert restore record to `backup_versions`

```python
# Example: during restore (backend startup)
def validate_backup_compatibility(backup_metadata):
    """Check if backup is compatible with current app."""
    current_version = get_app_version()  # from __version__
    backup_version = backup_metadata['app_version']
    
    if not is_compatible(current_version, backup_version):
        raise IncompatibleBackupError(
            f"Backup v{backup_version} incompatible with app v{current_version}"
        )
    
    # Check DB schema version
    current_schema = alembic_current()
    backup_schema = backup_metadata['db_schema_version']
    
    if current_schema < backup_schema:
        raise SchemaVersionError(
            f"DB schema too old: v{current_schema}, backup requires v{backup_schema}"
        )
    elif current_schema > backup_schema:
        log_migration_required(backup_schema, current_schema)
    
    # Check content version
    current_content_version = get_content_version()
    backup_content_version = backup_metadata['content_structure_version']
    
    if current_content_version > backup_content_version:
        log_content_migration_required(backup_content_version, current_content_version)
```

## Migration Strategy

### Levels of Change

1. **App-only changes** (UI, non-schema logic)
   - No DB migration needed
   - Content compatible as-is
   - Backup from any recent version works

2. **Schema-only changes** (DB migrations via Alembic)
   - DB migration required
   - Content needs to be re-indexed or transformed
   - Track migration in `migration_log`

3. **Content structure changes** (new fields, new format)
   - Content regeneration required
   - Old backups need transformation
   - Increment `content_structure_version`
   - May require full rebuild pipeline

4. **Breaking changes**
   - Incompatible schema + content structure
   - Requires careful rollout plan
   - May need blue/green deployment

### Compatibility Matrix

| App Version | DB Schema | Content Version | Status |
|---|---|---|---|
| 0.1.0 | 70 | 1 | EOL (unsupported) |
| 0.2.0 | 71 | 2 | Current |
| 0.2.1 | 71 | 2 | Compatible |
| 0.3.0 (planned) | 72 | 3 | Requires migration |

### Migration Checklist

When releasing with breaking changes:

- [ ] **Phase 1:** Release app version with both old and new schemas (dual-read)
- [ ] **Phase 2:** Run async migration job on all backups (generates manifests with new versions)
- [ ] **Phase 3:** Remove old schema support in next release
- [ ] **Phase 4:** Document migration in changelog + runbook

## Operational Commands

```bash
# Check backup compatibility before restore
jq . backups/2026-09-26_21-07/metadata.json

# List all backups with versions
for dir in backups/*/; do
  echo "$(basename $dir):"
  jq '{app_version, db_schema_version, content_structure_version}' $dir/metadata.json
done

# Check restore history
SELECT * FROM backup_versions ORDER BY restored_at DESC;

# Check migration status
SELECT * FROM migration_log WHERE status != 'completed' ORDER BY created_at;
```

## Benefits

1. **Safety:** Know exactly what app/DB/content versions go with each backup
2. **Auditability:** Track all restore operations and migrations
3. **Rollback:** Documented migration path to downgrade if needed
4. **Disaster Recovery:** Can validate backup before restoring
5. **Debugging:** Match logs to exact content version

## Implementation Phases

**Phase 1:** Update backup scripts to capture versions in metadata
**Phase 2:** Create migration tracking tables
**Phase 3:** Add validation logic at app startup
**Phase 4:** Build UI for backup history + restore compatibility check
