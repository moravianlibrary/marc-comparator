export const TaskType = {
  FetchRecord: "FetchRecord",
  FetchBatchOfRecords: "FetchBatchOfRecords",
  SyncRecords: "SyncRecords",
  LinkRecordsToAuthorities: "LinkRecordsToAuthorities",
  CompareRecords: "CompareRecords",
  ValidateRecords: "ValidateRecords",
  SetRecordVisibility: "SetRecordVisibility",
  DeleteTasks: "DeleteTasks",
  ProcessRecords: "ProcessRecords",
  RebuildAnalyticalData: "RebuildAnalyticalData",
} as const;

export type TaskType = (typeof TaskType)[keyof typeof TaskType];

export const TaskStatus = {
  Pending: "Pending",
  Started: "Started",
  Success: "Success",
  Failure: "Failure",
  Revoked: "Revoked",
} as const;

export type TaskStatus = (typeof TaskStatus)[keyof typeof TaskStatus];

export const TaskSeverity = {
  Info: "Info",
  Warning: "Warning",
  Error: "Error",
  Critical: "Critical",
} as const;

export type TaskSeverity = (typeof TaskSeverity)[keyof typeof TaskSeverity];

export interface Task {
  task_id: string;
  name: string;
  type: TaskType;
  status: TaskStatus;
  severity: TaskSeverity;
  progress: number | null;
  total: number | null;
  created_by: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}
