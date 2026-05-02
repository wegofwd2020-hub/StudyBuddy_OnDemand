import { adminClient } from "./admin-client";

export interface Backup {
  id: string;
  school_id: string;
  label: string;
  scope_type: string;
  scope_value: string | null;
  status: "pending" | "running" | "completed" | "failed";
  file_count: number;
  total_bytes: number;
  created_at: string;
  triggered_by: string | null;
}

export interface RestoreRequest {
  id: string;
  school_id: string;
  backup_id: string | null;
  status: string;
  scope_type: string;
  scope_value: string | null;
  side_by_side: boolean;
  conflict_catalog_id: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface BackupSchedule {
  school_id: string;
  cron: string | null;
}

// ── Admin API calls ───────────────────────────────────────────────────────────

export const listAllBackups = (page = 1, perPage = 20) =>
  adminClient
    .get(`/admin/backups?page=${page}&per_page=${perPage}`)
    .then((r) => r.data);

export const listSchoolBackups = (schoolId: string) =>
  adminClient.get(`/admin/schools/${schoolId}/backups`).then((r) => r.data);

export const createBackup = (
  schoolId: string,
  data: { scope_type: string; scope_value?: string; label?: string }
) =>
  adminClient
    .post(`/admin/schools/${schoolId}/backups`, data)
    .then((r) => r.data);

export const getBackup = (backupId: string) =>
  adminClient.get(`/admin/backups/${backupId}`).then((r) => r.data);

export const listAllRestoreRequests = () =>
  adminClient.get("/admin/restore-requests").then((r) => r.data);

export const acknowledgeRestoreRequest = (id: string) =>
  adminClient
    .patch(`/admin/restore-requests/${id}/acknowledge`)
    .then((r) => r.data);

export const executeRestoreRequest = (id: string) =>
  adminClient
    .patch(`/admin/restore-requests/${id}/execute`)
    .then((r) => r.data);

export const cancelRestoreRequest = (id: string) =>
  adminClient
    .patch(`/admin/restore-requests/${id}/cancel`)
    .then((r) => r.data);

export const listBackupSchedules = () =>
  adminClient.get("/admin/backup-schedules").then((r) => r.data);

export const updateBackupSchedule = (schoolId: string, cron: string) =>
  adminClient
    .put(`/admin/backup-schedules/${schoolId}`, { cron })
    .then((r) => r.data);
