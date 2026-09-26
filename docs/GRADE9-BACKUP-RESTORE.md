# Grade 9 Content Backup & Restore Strategy

## Current Implementation (2026-09-26)

### Scripts
- **backup-grade9-content.sh**: Tars `content_store_data/curricula/default-2026-g9*` to timestamped .tar.gz
- **restore-grade9-content.sh**: Restores from tarball, creates safety backup before overwrite

### Storage
- **Location**: `backups/grade9/` (local or `/opt/studybuddy/backups/grade9/` on demo)
- **Format**: `grade9-content-YYYYMMDD-HHMMSS.tar.gz`
- **Size**: ~3.9M per full Grade 9 curriculum
- **Compression**: gzip-9
- **Integrity**: SHA256 checksum printed on backup

### Limitations & Gaps

#### 1. **No Remote Storage**
- Backups stay on demo server's local disk
- **Risk**: Disk failure loses both primary + backup
- **Solution needed**: Upload to S3, Azure Blob, or Hetzner Cloud Snapshots

#### 2. **No Retention Policy**
- Backups accumulate indefinitely
- **Risk**: Disk fills up over time
- **Solution needed**: Keep-last-N policy (e.g., keep daily for 7d, weekly for 4w, monthly for 1y)

#### 3. **No Deduplication**
- Each backup is a full tar.gz
- **Risk**: Inefficient storage (no block-level dedup)
- **Solution needed**: Restic (like main backup.sh), or incremental tar snapshots

#### 4. **No Automation**
- Currently manual: `bash scripts/demo/backup-grade9-content.sh`
- **Risk**: Backups skipped or forgotten
- **Solution needed**: Cron job (daily at 02:00 UTC?) or CI/CD hook post-build

#### 5. **No Verification**
- Backup success = tar exit code 0
- **Risk**: Silent corruption (tarball unreadable but no error detected)
- **Solution needed**: `tar -tzf` test-extract after backup, periodic integrity checks

#### 6. **Single Point of Restore**
- Restore script is manual, no rollback history
- **Risk**: Accidental overwrite of good data with bad backup
- **Solution needed**: Snapshot tagging (e.g., tag "pre-g10-build"), restore-by-tag

---

## Proposed: Remote Backup + Retention

### Phase 1: Local Retention Policy (Quick Win)
**Timeline**: 1-2 hours  
**Effort**: Low

```bash
# scripts/demo/backup-grade9-content.sh (updated)
# After backup, delete old backups keeping only:
#   - Last 7 daily backups
#   - Last 4 weekly backups (1 per Monday)
#   - Last 3 monthly backups (1 per month-end)
#   - Last 1 yearly backup (Jan 1)

find backups/grade9/ -name "grade9-content-*.tar.gz" -mtime +7 -delete
```

**Pros**: Prevents disk fill  
**Cons**: Still local-only (no disaster recovery)

---

### Phase 2: S3/Azure Remote Upload (Medium Effort)
**Timeline**: 4-6 hours  
**Effort**: Medium

```bash
# After local backup, upload to S3
aws s3 cp backups/grade9/grade9-content-$TIMESTAMP.tar.gz \
  s3://studybuddy-backups/grade9-content/ \
  --storage-class GLACIER_IR \
  --metadata "host=$(hostname),timestamp=$TIMESTAMP,sha256=$CHECKSUM"
```

**Configuration needed**:
- AWS credentials in `.env.demo` (IAM role or key)
- S3 bucket with versioning + lifecycle policies
- Lifecycle: Move to Glacier after 30 days, delete after 90 days

**Pros**: Geographically redundant, cost-effective (Glacier)  
**Cons**: AWS dependency, restore latency (Glacier retrieval 1-5 min)

---

### Phase 3: Incremental Backups with Restic (Gold Standard)
**Timeline**: 8-12 hours  
**Effort**: High (but copy logic from existing `scripts/demo/backup.sh`)

```bash
# Leverage existing restic infrastructure
restic backup \
  --tag "grade9" \
  --tag "incremental" \
  content_store_data/curricula/default-2026-g9* \
  --exclude-caches

# Retention: 7 daily + 4 weekly + 3 monthly + 1 yearly
restic forget --tag "grade9" \
  --keep-daily 7 \
  --keep-weekly 4 \
  --keep-monthly 3 \
  --keep-yearly 1
```

**Pros**:
- Content-addressed dedup (3.9M becomes ~800K incremental)
- Encrypted at rest (AES-256)
- Per-snapshot integrity check
- Already using restic for DB backups (share repo/password)

**Cons**: Repo management overhead

---

## Proposed Ticket Structure

### Title
```
Epic: Improve Grade 9 (and all curricula) backup/restore strategy
```

### Sub-tasks

#### Task 1: Local Retention Policy
- [ ] Modify `backup-grade9-content.sh` to prune old backups
- [ ] Add config: `BACKUP_KEEP_DAYS=7`, `BACKUP_KEEP_WEEKS=4`
- [ ] Test on demo: verify 8-day-old backup deleted, 7-day kept
- [ ] Document: add to `CHEATSHEET.md`

#### Task 2: Remote S3 Upload
- [ ] Add AWS credentials to `.env.demo.example`
- [ ] Create `scripts/demo/upload-grade9-backup-s3.sh`
- [ ] Test: backup → upload → verify S3 listing
- [ ] Restore test: download from S3 → restore → verify content
- [ ] Document: CloudFormation or Terraform for bucket setup

#### Task 3: Restic Integration
- [ ] Extend `scripts/demo/backup.sh` to include `default-2026-g9*`
- [ ] Verify dedup (compare restic size vs raw tarball)
- [ ] Add restic restore path for Grade 9
- [ ] Test: backup, delete, restore, verify

#### Task 4: Automation (Cron + CI)
- [ ] Add cron job: `0 2 * * * bash /opt/studybuddy/scripts/demo/backup-grade9-content.sh`
- [ ] Or: post-build hook in CI (after grade pipeline completes)
- [ ] Monitor: track backup success/failure in observability (Prometheus)

#### Task 5: Verification & Testing
- [ ] Weekly integrity check: `tar -tzf backups/grade9/*.tar.gz | head` (spot-check)
- [ ] Monthly restore drill: restore to temp dir, verify lesson JSON parsing
- [ ] Document: add to runbook

---

## Retention Policy Matrix

| Backup Type | Keep Daily | Keep Weekly | Keep Monthly | Keep Yearly | Rationale |
|:---|:---:|:---:|:---:|:---:|:---|
| Grade 9 incremental (restic) | 7 | 4 | 3 | 1 | Recovery point SLA: recent issues vs long-term snapshots |
| Full curriculum (tar.gz) | 3 | 2 | 1 | 0 | Space-constrained; recent backups prioritized |
| Database (pg_dump + restic) | 7 | 4 | 3 | 1 | From existing policy; critical system state |

---

## Risk Mitigation Checklist

- [ ] **Backup before major ops**: Tag backup with `pre-g10-build`, `pre-migration-0074`, etc.
- [ ] **Test restore quarterly**: Restore to non-prod, verify 100% of lessons parse
- [ ] **Monitor backup jobs**: Alert if backup size drops >20% (possible data loss)
- [ ] **Encrypt in transit**: Use S3 HTTPS or restic encryption
- [ ] **Encrypt at rest**: S3 server-side encryption or restic AES-256
- [ ] **Separate credentials**: Backup AWS user has S3-only policy, no EC2/RDS access
- [ ] **Audit access**: Log who/when downloaded backups (S3 CloudTrail)

---

## Commands Reference

### Backup (current)
```bash
cd /opt/studybuddy
bash scripts/demo/backup-grade9-content.sh
# Output: backups/grade9/grade9-content-20260926-125252.tar.gz
```

### Restore (current)
```bash
cd /opt/studybuddy
bash scripts/demo/restore-grade9-content.sh backups/grade9/grade9-content-20260926-125252.tar.gz
# Prompts: Press Enter to proceed
# Creates: .grade9-pre-restore-[timestamp].tar.gz safety backup
```

### List backups
```bash
ls -lh backups/grade9/ | grep "\.tar\.gz$"
```

### Verify backup integrity
```bash
tar -tzf backups/grade9/grade9-content-20260926-125252.tar.gz | head
```

---

## See Also
- `scripts/demo/backup.sh` — full system backup (DB + content + .env) using restic
- `OPERATIONS.md` — runbooks for backup/restore procedures
- Epic 15 (BR-1 through BR-6) — curriculum backup & restore feature set
