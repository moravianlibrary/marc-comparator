import { z } from "zod";

export const PermissionSchema = z.enum([
    "ReadRecords",
    "AddRecords",
    "SyncRecordsFromCatalog",
    "RunRecordTasks",
    "ManageTasks",
    "ManageAllTasks",
    "ManageTaskSettings",
    "ManageAccessControl",
    "ManageAppSettings",
    "ManageSystem",
]);
export type Permission = z.infer<typeof PermissionSchema>;

export const PermissionsSchema = z.array(PermissionSchema);
export type Permissions = z.infer<typeof PermissionsSchema>;

export const PermissionDependencies: Record<Permission, Permission[]> = {
    ReadRecords: [],
    AddRecords: ["ReadRecords"],
    SyncRecordsFromCatalog: ["ReadRecords", "AddRecords"],
    RunRecordTasks: ["ReadRecords"],
    ManageTasks: ["RunRecordTasks"],
    ManageAllTasks: ["ManageTasks"],
    ManageTaskSettings: ["ManageTasks"],
    ManageAccessControl: [],
    ManageAppSettings: [],
    ManageSystem: ["ManageAppSettings", "ManageAccessControl"],
};
