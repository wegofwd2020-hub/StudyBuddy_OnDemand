"""
backend/src/backup/schemas.py

Pydantic request/response models for the backup and restore API.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


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
