export const TaskType = {
  FetchRecord: 'FetchRecord',
  FetchBatchOfRecords: 'FetchBatchOfRecords',
  SyncRecords: 'SyncRecords',
  LinkRecordsToAuthorities: 'LinkRecordsToAuthorities',
  CompareRecords: 'CompareRecords',
  ValidateRecords: 'ValidateRecords',
  SetRecordVisibility: 'SetRecordVisibility',
  DeleteTasks: 'DeleteTasks',
  ProcessRecords: 'ProcessRecords',
  RebuildAnalyticalData: 'RebuildAnalyticalData',
  CreateReport: 'CreateReport',
  HarvestPlugin: 'HarvestPlugin',
} as const;

export interface ReportArtifact {
  id: string;
  task_id: string;
  tool: string;
  filename: string;
  content_type: string;
  size: number;
  created_at: string;
}

export type TaskType = (typeof TaskType)[keyof typeof TaskType];

export const TaskStatus = {
  Pending: 'Pending',
  Started: 'Started',
  Success: 'Success',
  Failure: 'Failure',
  Revoked: 'Revoked',
} as const;

export type TaskStatus = (typeof TaskStatus)[keyof typeof TaskStatus];

export const TaskSeverity = {
  Info: 'Info',
  Warning: 'Warning',
  Error: 'Error',
  Critical: 'Critical',
} as const;

export type TaskSeverity = (typeof TaskSeverity)[keyof typeof TaskSeverity];

export interface Task {
  task_id: string;
  type: TaskType;
  /** What the task acts on (plugin, base); null when its type names nothing. */
  target?: string | null;
  status: TaskStatus;
  severity: TaskSeverity;
  progress: number | null;
  created_by: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}
