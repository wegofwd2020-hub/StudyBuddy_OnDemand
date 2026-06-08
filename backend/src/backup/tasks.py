"""
backend/src/backup/tasks.py

Celery tasks for curriculum backup and restore operations (Epic 15).

Task registry:
  backup_school_task            — snapshot a school's curricula to backup storage
  dry_run_restore_task          — verify a backup manifest + detect conflicts
  execute_restore_task          — apply a backup to the content store + DB
  send_backup_notification_task — email school contact on backup complete/failed
  dispatch_scheduled_backups    — coordinator: fan-out nightly per-school backups

All DB work uses short-lived asyncpg pools (min=1, max=3) with RLS bypass set
immediately after acquiring a connection.  Never uses the app-level pool.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

import asyncpg

from src.core.celery_app import _run_async, celery_app
from src.utils.logger import get_logger

log = get_logger("backup.tasks")


# ── helpers ───────────────────────────────────────────────────────────────────


async def _get_pool() -> asyncpg.Pool:
    from config import settings

    return await asyncpg.create_pool(
        settings.DATABASE_URL,
        min_size=1,
        max_size=3,
        statement_cache_size=0,
    )


async def _bypass(conn: asyncpg.Connection) -> None:
    """Stamp the RLS bypass on this connection."""
    await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


# ── Notification task ─────────────────────────────────────────────────────────


@celery_app.task(name="src.backup.tasks.send_backup_notification_task", bind=False)
def send_backup_notification_task(
    to_email: str,
    event: str,  # 'backup_completed' | 'backup_failed' | 'restore_completed' | 'restore_failed'
    school_id: str,
    backup_id: str,
    scope_type: str,
    scope_value: str | None = None,
    error_msg: str | None = None,
) -> None:
    """Send a simple notification email for backup/restore lifecycle events."""

    async def _send() -> None:
        from src.email.service import _send as send_email

        subject_map = {
            "backup_completed": f"StudyBuddy: Curriculum backup completed ({scope_type})",
            "backup_failed": f"StudyBuddy: Curriculum backup FAILED ({scope_type})",
            "restore_completed": f"StudyBuddy: Curriculum restore completed ({scope_type})",
            "restore_failed": f"StudyBuddy: Curriculum restore FAILED ({scope_type})",
        }
        subject = subject_map.get(event, f"StudyBuddy: Backup event — {event}")

        scope_label = f"{scope_type}" + (f": {scope_value}" if scope_value else "")
        if error_msg:
            text = (
                f"Event: {event}\n"
                f"School: {school_id}\n"
                f"Backup ID: {backup_id}\n"
                f"Scope: {scope_label}\n\n"
                f"Error: {error_msg}\n\n"
                "— The StudyBuddy Team"
            )
            html = (
                f"<p><strong>Event:</strong> {event}</p>"
                f"<p><strong>School:</strong> {school_id}</p>"
                f"<p><strong>Backup ID:</strong> {backup_id}</p>"
                f"<p><strong>Scope:</strong> {scope_label}</p>"
                f"<p style='color:#dc2626'><strong>Error:</strong> {error_msg}</p>"
                "<p>— The StudyBuddy Team</p>"
            )
        else:
            text = (
                f"Event: {event}\n"
                f"School: {school_id}\n"
                f"Backup ID: {backup_id}\n"
                f"Scope: {scope_label}\n\n"
                "— The StudyBuddy Team"
            )
            html = (
                f"<p><strong>Event:</strong> {event}</p>"
                f"<p><strong>School:</strong> {school_id}</p>"
                f"<p><strong>Backup ID:</strong> {backup_id}</p>"
                f"<p><strong>Scope:</strong> {scope_label}</p>"
                "<p>— The StudyBuddy Team</p>"
            )

        try:
            await send_email(
                to_email=to_email,
                subject=subject,
                text_body=text,
                html_body=html,
            )
        except Exception as exc:
            log.warning("backup_notification_email_failed", error=str(exc), to=to_email)

    _run_async(_send())


# ── Backup task ───────────────────────────────────────────────────────────────


@celery_app.task(name="src.backup.tasks.backup_school_task", bind=False)
def backup_school_task(
    school_id: str,
    scope_type: str,
    scope_value: str | None,
    triggered_by: str | None,
    backup_id: str,
) -> None:
    """
    Snapshot a school's curriculum data + content files to backup storage.

    Steps:
      1. Mark backup record as 'running'
      2. Query scoped DB rows (curricula, units, versions, llm_config, adoptions, packages)
      3. Walk content store files for each curriculum_id
      4. Upload backup_data.json, content files, manifest.json
      5. Update backup record to 'completed' with file counts + manifest
      6. Prune excess backups beyond BACKUP_MAX_PER_SCHOOL
      7. Fire audit event + send email
    """

    async def _do() -> None:
        from config import settings

        from src.backup.manifest import BackupManifest, ManifestEntry, sha256_bytes
        from src.backup.storage import get_backup_storage
        from src.core.events import write_audit_log

        pool = await _get_pool()
        school_uuid = uuid.UUID(school_id)
        triggered_uuid = uuid.UUID(triggered_by) if triggered_by else None
        contact_email: str | None = None

        try:
            async with pool.acquire() as conn:
                await _bypass(conn)

                # Mark running
                await conn.execute(
                    "UPDATE curriculum_backups SET status='running' WHERE id=$1",
                    uuid.UUID(backup_id),
                )

                # Fetch school contact email for notification
                school_row = await conn.fetchrow(
                    "SELECT contact_email FROM schools WHERE school_id=$1", school_uuid
                )
                if school_row:
                    contact_email = school_row["contact_email"]

                # Query scoped curricula
                if scope_type == "grade":
                    curricula_rows = await conn.fetch(
                        """
                        SELECT * FROM curricula
                        WHERE school_id=$1 AND grade=$2::int
                        """,
                        school_uuid,
                        int(scope_value) if scope_value else 0,
                    )
                elif scope_type == "name":
                    curricula_rows = await conn.fetch(
                        """
                        SELECT * FROM curricula
                        WHERE school_id=$1 AND name ILIKE $2
                        """,
                        school_uuid,
                        f"%{scope_value}%" if scope_value else "%",
                    )
                else:  # full
                    curricula_rows = await conn.fetch(
                        "SELECT * FROM curricula WHERE school_id=$1",
                        school_uuid,
                    )

                # curricula PK is curriculum_id (TEXT), not id. curriculum_id is
                # also TEXT on curriculum_units and content_subject_versions, so
                # pass the IDs through as text — never wrap in uuid.UUID().
                curriculum_ids = [str(r["curriculum_id"]) for r in curricula_rows]

                # Query dependent rows
                units_rows: list = []
                versions_rows: list = []
                if curriculum_ids:
                    units_rows = await conn.fetch(
                        "SELECT * FROM curriculum_units WHERE curriculum_id = ANY($1)",
                        curriculum_ids,
                    )
                    versions_rows = await conn.fetch(
                        "SELECT * FROM content_subject_versions WHERE curriculum_id = ANY($1)",
                        curriculum_ids,
                    )

                llm_config_row = await conn.fetchrow(
                    "SELECT * FROM school_llm_config WHERE school_id=$1", school_uuid
                )

                adoptions_rows = await conn.fetch(
                    "SELECT * FROM school_adopted_curricula WHERE school_id=$1", school_uuid
                )

                packages_rows = await conn.fetch(
                    """
                    SELECT cp.* FROM classroom_packages cp
                    JOIN classrooms cl ON cl.classroom_id = cp.classroom_id
                    WHERE cl.school_id=$1
                    """,
                    school_uuid,
                )

            # Serialize DB data
            def _row_to_dict(r: asyncpg.Record) -> dict:
                d = dict(r)
                for k, v in d.items():
                    if isinstance(v, uuid.UUID):
                        d[k] = str(v)
                    elif isinstance(v, datetime):
                        d[k] = v.isoformat()
                return d

            backup_data = {
                "curricula": [_row_to_dict(r) for r in curricula_rows],
                "curriculum_units": [_row_to_dict(r) for r in units_rows],
                "content_subject_versions": [_row_to_dict(r) for r in versions_rows],
                "school_llm_config": _row_to_dict(llm_config_row) if llm_config_row else None,
                "school_adopted_curricula": [_row_to_dict(r) for r in adoptions_rows],
                "classroom_packages": [_row_to_dict(r) for r in packages_rows],
            }
            backup_data_bytes = json.dumps(backup_data, indent=2).encode()

            # Walk content store files
            manifest = BackupManifest(
                backup_id=backup_id,
                school_id=school_id,
                scope_type=scope_type,
                scope_value=scope_value,
                created_at=_now_iso(),
                db_row_counts={
                    "curricula": len(curricula_rows),
                    "curriculum_units": len(units_rows),
                    "content_subject_versions": len(versions_rows),
                },
            )

            storage = get_backup_storage()
            content_root = Path(settings.CONTENT_STORE_PATH)

            # Upload backup_data.json
            db_path = f"{school_id}/{backup_id}/backup_data.json"
            await storage.upload(db_path, backup_data_bytes)
            manifest.entries.append(
                ManifestEntry(
                    path=db_path,
                    sha256=sha256_bytes(backup_data_bytes),
                    size_bytes=len(backup_data_bytes),
                )
            )

            # Walk and upload content files for each curriculum
            for cur_id in curriculum_ids:
                cur_content_dir = content_root / "curricula" / cur_id
                if not cur_content_dir.exists():
                    continue
                for file_path in cur_content_dir.rglob("*"):
                    if not file_path.is_file():
                        continue
                    file_bytes = file_path.read_bytes()
                    relative = file_path.relative_to(content_root)
                    dest_path = f"{school_id}/{backup_id}/content/{relative}"
                    await storage.upload(dest_path, file_bytes)
                    manifest.entries.append(
                        ManifestEntry(
                            path=dest_path,
                            sha256=sha256_bytes(file_bytes),
                            size_bytes=len(file_bytes),
                        )
                    )

            # Upload manifest last
            manifest_bytes = manifest.to_json()
            manifest_path = f"{school_id}/{backup_id}/manifest.json"
            await storage.upload(manifest_path, manifest_bytes)
            manifest.entries.append(
                ManifestEntry(
                    path=manifest_path,
                    sha256=sha256_bytes(manifest_bytes),
                    size_bytes=len(manifest_bytes),
                )
            )

            total_bytes = sum(e.size_bytes for e in manifest.entries)
            file_count = len(manifest.entries)
            manifest_dict = json.loads(manifest.to_json())

            # Update DB record to completed
            pool2 = await _get_pool()
            try:
                async with pool2.acquire() as conn:
                    await _bypass(conn)
                    await conn.execute(
                        """
                        UPDATE curriculum_backups
                        SET status='completed',
                            file_count=$2,
                            total_bytes=$3,
                            manifest_json=$4,
                            storage_path=$5
                        WHERE id=$1
                        """,
                        uuid.UUID(backup_id),
                        file_count,
                        total_bytes,
                        json.dumps(manifest_dict),
                        f"{school_id}/{backup_id}",
                    )

                    # Prune excess backups
                    from config import settings as cfg

                    all_backups = await conn.fetch(
                        """
                        SELECT id, storage_path FROM curriculum_backups
                        WHERE school_id=$1
                        ORDER BY created_at DESC
                        """,
                        school_uuid,
                    )
                    if len(all_backups) > cfg.BACKUP_MAX_PER_SCHOOL:
                        excess = all_backups[cfg.BACKUP_MAX_PER_SCHOOL :]
                        for old in excess:
                            old_id = str(old["id"])
                            old_path = old["storage_path"] or ""
                            if old_path:
                                try:
                                    old_keys = await storage.list_prefix(old_path)
                                    for k in old_keys:
                                        await storage.delete(k)
                                except Exception as prune_exc:
                                    log.warning(
                                        "backup_prune_storage_error",
                                        backup_id=old_id,
                                        error=str(prune_exc),
                                    )
                            await conn.execute(
                                "DELETE FROM curriculum_backups WHERE id=$1",
                                uuid.UUID(old_id),
                            )
                            log.info("backup_pruned", old_backup_id=old_id)
            finally:
                await pool2.close()

            # Audit event
            if triggered_uuid:
                write_audit_log(
                    event_type="curriculum.backup_created",
                    actor_type="admin",
                    actor_id=triggered_uuid,
                    target_type="school",
                    target_id=school_uuid,
                    metadata={
                        "backup_id": backup_id,
                        "scope_type": scope_type,
                        "scope_value": scope_value,
                        "file_count": file_count,
                    },
                )

            log.info(
                "backup_completed",
                backup_id=backup_id,
                school_id=school_id,
                file_count=file_count,
                total_bytes=total_bytes,
            )

            if contact_email:
                send_backup_notification_task.delay(
                    to_email=contact_email,
                    event="backup_completed",
                    school_id=school_id,
                    backup_id=backup_id,
                    scope_type=scope_type,
                    scope_value=scope_value,
                )

        except Exception as exc:
            log.error("backup_failed", backup_id=backup_id, error=str(exc), exc_info=exc)
            # Mark failed
            try:
                fail_pool = await _get_pool()
                try:
                    async with fail_pool.acquire() as conn:
                        await _bypass(conn)
                        await conn.execute(
                            "UPDATE curriculum_backups SET status='failed' WHERE id=$1",
                            uuid.UUID(backup_id),
                        )
                finally:
                    await fail_pool.close()
            except Exception as inner:
                log.error("backup_failed_mark_error", error=str(inner))
            if contact_email:
                send_backup_notification_task.delay(
                    to_email=contact_email,
                    event="backup_failed",
                    school_id=school_id,
                    backup_id=backup_id,
                    scope_type=scope_type,
                    scope_value=scope_value,
                    error_msg=str(exc),
                )
            raise
        finally:
            await pool.close()

    _run_async(_do())


# ── Dry-run restore task ──────────────────────────────────────────────────────


@celery_app.task(name="src.backup.tasks.dry_run_restore_task", bind=False)
def dry_run_restore_task(request_id: str) -> None:
    """
    Verify backup integrity and detect conflicts before committing a restore.

    1. Set request status = 'dry_run'
    2. Load manifest from backup storage
    3. Sample-verify SHA-256 (10% of entries, max 50)
    4. Check for conflicting content_subject_versions updated after backup.created_at
    5a. No conflicts → advance to 'in_progress', dispatch execute_restore_task
    5b. Conflicts → create staging curriculum, set request to 'awaiting_school_confirm',
        email school contact + super-admin
    """

    async def _do() -> None:
        import random

        from src.backup.manifest import BackupManifest, sha256_bytes
        from src.backup.storage import get_backup_storage

        pool = await _get_pool()
        try:
            async with pool.acquire() as conn:
                await _bypass(conn)

                # Fetch request
                req = await conn.fetchrow(
                    "SELECT * FROM backup_restore_requests WHERE id=$1",
                    uuid.UUID(request_id),
                )
                if not req:
                    log.error("dry_run_request_not_found", request_id=request_id)
                    return

                school_id = str(req["school_id"])
                backup_id = str(req["backup_id"])
                scope_type = req["scope_type"]
                scope_value = req["scope_value"]

                # Mark dry_run
                await conn.execute(
                    "UPDATE backup_restore_requests SET status='dry_run', updated_at=NOW() WHERE id=$1",
                    uuid.UUID(request_id),
                )

                # Fetch backup record for created_at
                backup_row = await conn.fetchrow(
                    "SELECT * FROM curriculum_backups WHERE id=$1",
                    uuid.UUID(backup_id),
                )
                if not backup_row:
                    raise ValueError(f"Backup {backup_id} not found")

                backup_created_at = backup_row["created_at"]

                # Fetch school contact email
                school_row = await conn.fetchrow(
                    "SELECT contact_email FROM schools WHERE school_id=$1",
                    uuid.UUID(school_id),
                )
                contact_email = school_row["contact_email"] if school_row else None

            # Load manifest
            storage = get_backup_storage()
            manifest_bytes = await storage.download(f"{school_id}/{backup_id}/manifest.json")
            manifest = BackupManifest.from_json(manifest_bytes)

            # Sample-verify SHA-256
            content_entries = [e for e in manifest.entries if "/content/" in e.path]
            sample_size = min(max(1, len(content_entries) // 10), 50)
            sample = random.sample(content_entries, min(sample_size, len(content_entries)))

            for entry in sample:
                actual_bytes = await storage.download(entry.path)
                actual_sha = sha256_bytes(actual_bytes)
                if actual_sha != entry.sha256:
                    raise ValueError(
                        f"SHA-256 mismatch for {entry.path}: "
                        f"expected {entry.sha256}, got {actual_sha}"
                    )

            # Detect conflicts: content_subject_versions updated after backup.created_at
            # for curricula in the backup scope
            pool2 = await _get_pool()
            conflicts: list[dict] = []
            staging_curriculum_id: str | None = None
            try:
                async with pool2.acquire() as conn:
                    await _bypass(conn)

                    # Get curriculum IDs from the backup data
                    backup_data_bytes = await storage.download(
                        f"{school_id}/{backup_id}/backup_data.json"
                    )
                    backup_data = json.loads(backup_data_bytes)
                    curriculum_ids = [c["id"] for c in backup_data.get("curricula", [])]

                    if curriculum_ids:
                        c_uuids = [uuid.UUID(c) for c in curriculum_ids]
                        conflict_rows = await conn.fetch(
                            """
                            SELECT id, curriculum_id, subject, version_number, updated_at
                            FROM content_subject_versions
                            WHERE curriculum_id = ANY($1)
                              AND updated_at > $2
                            """,
                            c_uuids,
                            backup_created_at,
                        )
                        conflicts = [dict(r) for r in conflict_rows]

                    if not conflicts:
                        # No conflicts — advance to in_progress
                        await conn.execute(
                            """
                            UPDATE backup_restore_requests
                            SET status='in_progress', updated_at=NOW()
                            WHERE id=$1
                            """,
                            uuid.UUID(request_id),
                        )
                        log.info(
                            "dry_run_no_conflicts_advancing",
                            request_id=request_id,
                        )
                    else:
                        # Create a staging curriculum row
                        today_str = datetime.now(tz=UTC).strftime("%Y%m%d")
                        # Use first curriculum name for staging label
                        orig_name = (
                            backup_data["curricula"][0].get("name", "unknown")
                            if backup_data.get("curricula")
                            else "unknown"
                        )
                        staging_name = f"{orig_name}.restore-staging.{today_str}"
                        staging_row = await conn.fetchrow(
                            """
                            INSERT INTO curricula
                                (school_id, name, grade, owner_type, status)
                            VALUES ($1, $2, $3, 'school', 'draft')
                            RETURNING id
                            """,
                            uuid.UUID(school_id),
                            staging_name,
                            backup_data["curricula"][0].get("grade", 0)
                            if backup_data.get("curricula")
                            else 0,
                        )
                        staging_curriculum_id = str(staging_row["id"])

                        await conn.execute(
                            """
                            UPDATE backup_restore_requests
                            SET status='awaiting_school_confirm',
                                conflict_catalog_id=$2,
                                updated_at=NOW()
                            WHERE id=$1
                            """,
                            uuid.UUID(request_id),
                            uuid.UUID(staging_curriculum_id),
                        )
                        log.info(
                            "dry_run_conflicts_found",
                            request_id=request_id,
                            conflict_count=len(conflicts),
                            staging_curriculum_id=staging_curriculum_id,
                        )

                        # Email school contact + super-admin about conflicts
                        conflict_summary = "\n".join(
                            f"  - subject={c.get('subject')} version={c.get('version_number')} "
                            f"updated={c.get('updated_at')}"
                            for c in conflicts[:20]
                        )
                        if contact_email:
                            send_backup_notification_task.delay(
                                to_email=contact_email,
                                event="restore_awaiting_confirm",
                                school_id=school_id,
                                backup_id=backup_id,
                                scope_type=scope_type,
                                scope_value=scope_value,
                                error_msg=(
                                    f"{len(conflicts)} conflicting content versions found "
                                    f"(updated after backup):\n{conflict_summary}\n\n"
                                    f"A staging curriculum has been created: {staging_name}"
                                ),
                            )
            finally:
                await pool2.close()

            # Dispatch execute_restore_task if no conflicts
            if not conflicts:
                execute_restore_task.delay(request_id=request_id)

        except Exception as exc:
            log.error("dry_run_failed", request_id=request_id, error=str(exc), exc_info=exc)
            fail_pool = await _get_pool()
            try:
                async with fail_pool.acquire() as conn:
                    await _bypass(conn)
                    await conn.execute(
                        "UPDATE backup_restore_requests SET status='failed', updated_at=NOW() WHERE id=$1",
                        uuid.UUID(request_id),
                    )
            finally:
                await fail_pool.close()
            raise
        finally:
            await pool.close()

    _run_async(_do())


# ── Execute restore task ──────────────────────────────────────────────────────


@celery_app.task(name="src.backup.tasks.execute_restore_task", bind=False)
def execute_restore_task(request_id: str) -> None:
    """
    Apply a backup to the content store and database.

    1. Set request status = 'in_progress'
    2. Re-download and full-verify manifest SHA-256
    3. Parse backup_data.json
    4. Determine target: side_by_side → new curricula named {name}.{yyyymmdd},
       otherwise upsert existing rows
    5. Write content files from backup storage → content store
    6. Set request status = 'completed'
    7. Audit event + email
    """

    async def _do() -> None:
        from config import settings

        from src.backup.manifest import BackupManifest, sha256_bytes
        from src.backup.storage import get_backup_storage
        from src.core.events import write_audit_log

        pool = await _get_pool()
        school_id: str | None = None
        backup_id: str | None = None
        contact_email: str | None = None

        try:
            async with pool.acquire() as conn:
                await _bypass(conn)

                req = await conn.fetchrow(
                    "SELECT * FROM backup_restore_requests WHERE id=$1",
                    uuid.UUID(request_id),
                )
                if not req:
                    log.error("execute_restore_request_not_found", request_id=request_id)
                    return

                school_id = str(req["school_id"])
                backup_id = str(req["backup_id"])
                scope_type = req["scope_type"]
                scope_value = req["scope_value"]
                side_by_side = req["side_by_side"]

                await conn.execute(
                    "UPDATE backup_restore_requests SET status='in_progress', updated_at=NOW() WHERE id=$1",
                    uuid.UUID(request_id),
                )

                school_row = await conn.fetchrow(
                    "SELECT contact_email FROM schools WHERE school_id=$1",
                    uuid.UUID(school_id),
                )
                if school_row:
                    contact_email = school_row["contact_email"]

            # Load and fully verify manifest
            storage = get_backup_storage()
            manifest_bytes = await storage.download(f"{school_id}/{backup_id}/manifest.json")
            manifest = BackupManifest.from_json(manifest_bytes)

            for entry in manifest.entries:
                if entry.path.endswith("manifest.json"):
                    continue  # manifest can't verify itself
                actual_bytes = await storage.download(entry.path)
                actual_sha = sha256_bytes(actual_bytes)
                if actual_sha != entry.sha256:
                    raise ValueError(
                        f"SHA-256 mismatch during restore for {entry.path}: "
                        f"expected {entry.sha256}, got {actual_sha}"
                    )

            # Load backup data
            backup_data_bytes = await storage.download(f"{school_id}/{backup_id}/backup_data.json")
            backup_data = json.loads(backup_data_bytes)

            content_root = Path(settings.CONTENT_STORE_PATH)
            today_str = datetime.now(tz=UTC).strftime("%Y%m%d")

            pool2 = await _get_pool()
            try:
                async with pool2.acquire() as conn:
                    await _bypass(conn)

                    for cur in backup_data.get("curricula", []):
                        orig_id = cur["id"]
                        if side_by_side:
                            # Create a new curriculum row with a dated name
                            new_name = f"{cur.get('name', orig_id)}.{today_str}"
                            new_row = await conn.fetchrow(
                                """
                                INSERT INTO curricula
                                    (school_id, name, grade, owner_type, status, stream_code)
                                VALUES ($1, $2, $3, $4, $5, $6)
                                RETURNING id
                                """,
                                uuid.UUID(school_id),
                                new_name,
                                cur.get("grade", 0),
                                cur.get("owner_type", "school"),
                                cur.get("status", "active"),
                                cur.get("stream_code"),
                            )
                            target_id = str(new_row["id"])
                        else:
                            # Upsert into existing curriculum row
                            await conn.execute(
                                """
                                INSERT INTO curricula
                                    (id, school_id, name, grade, owner_type, status, stream_code)
                                VALUES ($1, $2, $3, $4, $5, $6, $7)
                                ON CONFLICT (id) DO UPDATE
                                SET name=$3, grade=$4, owner_type=$5,
                                    status=$6, stream_code=$7
                                """,
                                uuid.UUID(orig_id),
                                uuid.UUID(school_id),
                                cur.get("name", ""),
                                cur.get("grade", 0),
                                cur.get("owner_type", "school"),
                                cur.get("status", "active"),
                                cur.get("stream_code"),
                            )
                            target_id = orig_id

                        # Restore curriculum_units
                        for unit in backup_data.get("curriculum_units", []):
                            if unit.get("curriculum_id") != orig_id:
                                continue
                            await conn.execute(
                                """
                                INSERT INTO curriculum_units
                                    (id, curriculum_id, unit_id, title, unit_name,
                                     subject, grade, has_lab, ordering)
                                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                                ON CONFLICT (id) DO UPDATE
                                SET title=$4, unit_name=$5, subject=$6,
                                    grade=$7, has_lab=$8, ordering=$9
                                """,
                                uuid.UUID(unit["id"]),
                                uuid.UUID(target_id),
                                unit.get("unit_id", ""),
                                unit.get("title", ""),
                                unit.get("unit_name") or unit.get("title", ""),
                                unit.get("subject", ""),
                                unit.get("grade", 0),
                                unit.get("has_lab", False),
                                unit.get("ordering", 0),
                            )

                    # Write content files from backup storage to content store
                    content_prefix = f"{school_id}/{backup_id}/content/"
                    content_keys = await storage.list_prefix(f"{school_id}/{backup_id}/content")
                    for key in content_keys:
                        file_bytes = await storage.download(key)
                        # key is like: {school_id}/{backup_id}/content/curricula/{cur_id}/...
                        rel = key.removeprefix(content_prefix)
                        dest = content_root / rel
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_bytes(file_bytes)

            finally:
                await pool2.close()

            # Mark completed
            pool3 = await _get_pool()
            try:
                async with pool3.acquire() as conn:
                    await _bypass(conn)
                    await conn.execute(
                        "UPDATE backup_restore_requests SET status='completed', updated_at=NOW() WHERE id=$1",
                        uuid.UUID(request_id),
                    )
            finally:
                await pool3.close()

            # Audit
            write_audit_log(
                event_type="restore.completed",
                actor_type="system",
                actor_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
                target_type="school",
                target_id=uuid.UUID(school_id),
                metadata={
                    "request_id": request_id,
                    "backup_id": backup_id,
                    "side_by_side": side_by_side,
                },
            )

            log.info(
                "restore_completed",
                request_id=request_id,
                school_id=school_id,
                backup_id=backup_id,
            )

            if contact_email:
                send_backup_notification_task.delay(
                    to_email=contact_email,
                    event="restore_completed",
                    school_id=school_id,
                    backup_id=backup_id,
                    scope_type=scope_type,
                    scope_value=scope_value,
                )

        except Exception as exc:
            log.error("restore_failed", request_id=request_id, error=str(exc), exc_info=exc)
            try:
                fail_pool = await _get_pool()
                try:
                    async with fail_pool.acquire() as conn:
                        await _bypass(conn)
                        await conn.execute(
                            "UPDATE backup_restore_requests SET status='failed', updated_at=NOW() WHERE id=$1",
                            uuid.UUID(request_id),
                        )
                finally:
                    await fail_pool.close()
            except Exception as inner:
                log.error("restore_failed_mark_error", error=str(inner))

            if school_id and backup_id and contact_email:
                send_backup_notification_task.delay(
                    to_email=contact_email,
                    event="restore_failed",
                    school_id=school_id,
                    backup_id=backup_id,
                    scope_type="unknown",
                    scope_value=None,
                    error_msg=str(exc),
                )

            # Audit failure
            if school_id:
                write_audit_log(
                    event_type="restore.failed",
                    actor_type="system",
                    actor_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
                    target_type="school",
                    target_id=uuid.UUID(school_id),
                    metadata={"request_id": request_id, "error": str(exc)},
                )
            raise
        finally:
            await pool.close()

    _run_async(_do())


# ── Scheduled backup coordinator ──────────────────────────────────────────────


@celery_app.task(name="src.backup.tasks.dispatch_scheduled_backups", bind=False)
def dispatch_scheduled_backups() -> None:
    """
    Nightly coordinator: query all schools with a non-null backup_cron and
    dispatch backup_school_task for each.

    The per-school cron expression is stored in schools.backup_cron but the
    nightly dispatch is triggered by this single Beat entry at 02:30 UTC.
    Individual per-school scheduling (respecting the actual cron expression)
    is a future enhancement; for now every school with backup_cron set gets
    a nightly full backup triggered by this task.
    """

    async def _do() -> None:
        pool = await _get_pool()
        try:
            async with pool.acquire() as conn:
                await _bypass(conn)
                schools = await conn.fetch(
                    """
                    SELECT school_id FROM schools
                    WHERE backup_cron IS NOT NULL AND backup_cron != ''
                    """
                )

            for school_row in schools:
                sid = str(school_row["school_id"])
                new_backup_id = str(uuid.uuid4())

                # Create the pending record
                record_pool = await _get_pool()
                try:
                    async with record_pool.acquire() as conn:
                        await _bypass(conn)
                        row = await conn.fetchrow(
                            """
                            INSERT INTO curriculum_backups
                                (id, school_id, label, scope_type, status)
                            VALUES ($1, $2, 'nightly', 'full', 'pending')
                            RETURNING id
                            """,
                            uuid.UUID(new_backup_id),
                            uuid.UUID(sid),
                        )
                        new_backup_id = str(row["id"])
                finally:
                    await record_pool.close()

                backup_school_task.delay(
                    school_id=sid,
                    scope_type="full",
                    scope_value=None,
                    triggered_by=None,
                    backup_id=new_backup_id,
                )
                log.info("scheduled_backup_dispatched", school_id=sid, backup_id=new_backup_id)

            log.info("dispatch_scheduled_backups_done", school_count=len(schools))
        finally:
            await pool.close()

    _run_async(_do())
