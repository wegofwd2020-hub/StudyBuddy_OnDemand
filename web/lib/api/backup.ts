import adminClient from "./admin-client";
import schoolApi from "./school-client";

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
  scheduled_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface BackupSchedule {
  school_id: string;
  cron: string | null;
}

// ── Admin API calls ───────────────────────────────────────────────────────────

export const listAllBackups = (page = 1, perPage = 20) =>
  adminClient.get(`/admin/backups?page=${page}&per_page=${perPage}`).then((r) => r.data);

export const listSchoolBackups = (schoolId: string) =>
  adminClient.get(`/admin/schools/${schoolId}/backups`).then((r) => r.data);

export const createBackup = (
  schoolId: string,
  data: { scope_type: string; scope_value?: string; label?: string },
) => adminClient.post(`/admin/schools/${schoolId}/backups`, data).then((r) => r.data);

export const getBackup = (backupId: string) =>
  adminClient.get(`/admin/backups/${backupId}`).then((r) => r.data);

export const listAllRestoreRequests = () =>
  adminClient.get("/admin/restore-requests").then((r) => r.data);

export const acknowledgeRestoreRequest = (id: string) =>
  adminClient.patch(`/admin/restore-requests/${id}/acknowledge`).then((r) => r.data);

export const executeRestoreRequest = (id: string) =>
  adminClient.patch(`/admin/restore-requests/${id}/execute`).then((r) => r.data);

export const cancelRestoreRequest = (id: string) =>
  adminClient.patch(`/admin/restore-requests/${id}/cancel`).then((r) => r.data);

export const listBackupSchedules = () =>
  adminClient.get("/admin/backup-schedules").then((r) => r.data);

export const updateBackupSchedule = (schoolId: string, cron: string) =>
  adminClient.put(`/admin/backup-schedules/${schoolId}`, { cron }).then((r) => r.data);

// ── School portal API calls ───────────────────────────────────────────────────

export const schoolListBackups = (schoolId: string) =>
  schoolApi.get(`/schools/${schoolId}/backups`).then((r) => r.data);

export const schoolListRestoreRequests = (schoolId: string) =>
  schoolApi.get(`/schools/${schoolId}/restore-requests`).then((r) => r.data);

export const schoolGetRestoreRequest = (schoolId: string, requestId: string) =>
  schoolApi.get(`/schools/${schoolId}/restore-requests/${requestId}`).then((r) => r.data);

export const schoolSubmitRestoreRequest = (
  schoolId: string,
  data: {
    backup_id: string;
    scope_type: string;
    scope_value?: string;
    notes?: string;
    side_by_side?: boolean;
    scheduled_at?: string;
  },
) => schoolApi.post(`/schools/${schoolId}/restore-requests`, data).then((r) => r.data);

export const schoolConfirmRestore = (
  schoolId: string,
  requestId: string,
  sideBySide: boolean,
) =>
  schoolApi
    .patch(`/schools/${schoolId}/restore-requests/${requestId}/confirm`, {
      side_by_side: sideBySide,
    })
    .then((r) => r.data);

export const schoolCancelRestoreRequest = (schoolId: string, requestId: string) =>
  schoolApi
    .patch(`/schools/${schoolId}/restore-requests/${requestId}/cancel`)
    .then((r) => r.data);
