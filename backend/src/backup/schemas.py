"""
backend/src/backup/schemas.py

Pydantic request/response models for the backup and restore API.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, field_validator

# `scheduled_at` on a restore request is a *preferred* time, not a promise of
# unattended execution — nothing in the system ever polls this column and
# auto-dispatches a restore (see issue #589: a school scheduled one for 2030
# and it just sat in `submitted` forever). The restore lifecycle
# (submitted -> acknowledged -> in_progress -> completed) only ever advances
# on a human button click (super_admin acknowledge/execute, or school
# confirm). Bound the horizon so the field can't be (mis)used to imply a
# scheduling system that doesn't exist; a school admin checking in weekly is
# well within this window, and anything further out reads as confusion about
# what the field does rather than a genuine near-term preference.
RESTORE_SCHEDULE_MAX_HORIZON_DAYS = 30


class BackupCreateRequest(BaseModel):
    scope_type: str  # 'grade' | 'name' | 'full'
    scope_value: str | None = None
    label: str = ""


class BackupResponse(BaseModel):
    id: str
    school_id: str
    label: str
    scope_type: str
    scope_value: str | None
    status: str
    file_count: int
    total_bytes: int
    created_at: datetime
    triggered_by: str | None


class BackupListResponse(BaseModel):
    backups: list[BackupResponse]
    total: int


class RestoreRequestCreate(BaseModel):
    backup_id: str
    scope_type: str
    scope_value: str | None = None
    notes: str | None = None
    scheduled_at: datetime | None = None
    side_by_side: bool = False

    @field_validator("scheduled_at")
    @classmethod
    def validate_scheduled_at(cls, v: datetime | None) -> datetime | None:
        """Bound `scheduled_at` so it can't imply automatic scheduling.

        Blank stays valid ("as soon as an administrator can action it").
        A supplied value must be a genuine near-term preference: not in the
        past, and not further out than an administrator would realistically
        be checking this queue.
        """
        if v is None:
            return v
        now = datetime.now(UTC)
        v_aware = v if v.tzinfo is not None else v.replace(tzinfo=UTC)
        if v_aware < now:
            raise ValueError("scheduled_at cannot be in the past.")
        horizon = now + timedelta(days=RESTORE_SCHEDULE_MAX_HORIZON_DAYS)
        if v_aware > horizon:
            raise ValueError(
                f"scheduled_at cannot be more than {RESTORE_SCHEDULE_MAX_HORIZON_DAYS} "
                "days out. Restore requests are reviewed and actioned by an "
                "administrator, not executed automatically at the requested time — "
                "pick a nearer date or leave this blank."
            )
        return v


class RestoreRequestResponse(BaseModel):
    id: str
    school_id: str
    backup_id: str | None
    status: str
    scope_type: str
    scope_value: str | None
    side_by_side: bool
    conflict_catalog_id: str | None
    scheduled_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class RestoreRequestListResponse(BaseModel):
    requests: list[RestoreRequestResponse]
    total: int


class BackupScheduleUpdate(BaseModel):
    cron: str  # e.g. "0 2 * * *"


class BackupScheduleResponse(BaseModel):
    school_id: str
    cron: str | None


class ConfirmOverrideRequest(BaseModel):
    side_by_side: bool = False
