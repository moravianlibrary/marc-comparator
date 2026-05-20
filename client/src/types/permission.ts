export const Permission = {
  ReadRecords: "ReadRecords",
  AddRecords: "AddRecords",
  SyncRecordsFromCatalog: "SyncRecordsFromCatalog",
  RunRecordTasks: "RunRecordTasks",
  ManageTasks: "ManageTasks",
  ManageAllTasks: "ManageAllTasks",
  ManageAccessControl: "ManageAccessControl",
  ManageAppSettings: "ManageAppSettings",
  ManageTaskSettings: "ManageTaskSettings",
  ManageSystem: "ManageSystem",
} as const;

export type Permission = (typeof Permission)[keyof typeof Permission];

export type PermissionGuard =
  | Permission
  | { any: Permission[] }
  | { all: Permission[] };
