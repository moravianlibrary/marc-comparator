import { z } from "zod";

export const PermissionSchema = z.enum([
    "ReadRecords",
    "AddRecords",
    "SyncRecordsFromCatalog",
    "RunRecordTasks",
    "ManageTasks",
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
    ManageTaskSettings: ["ManageTasks"],
    ManageAccessControl: [],
    ManageAppSettings: [],
    ManageSystem: ["ManageAppSettings", "ManageAccessControl"],
};
