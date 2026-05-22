export const Permission = {
  ReadRecords: "ReadRecords",
  ReviewRecords: "ReviewRecords",
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

export const PermissionDependencies: Record<Permission, Permission[]> = {
  ReadRecords: [],
  ReviewRecords: ["ReadRecords"],
  AddRecords: ["ReadRecords"],
  SyncRecordsFromCatalog: ["ReadRecords", "AddRecords", "ManageTasks"],
  RunRecordTasks: ["ReadRecords"],
  ManageTasks: ["RunRecordTasks"],
  ManageAllTasks: ["ManageTasks"],
  ManageTaskSettings: ["ManageTasks"],
  ManageAccessControl: [],
  ManageAppSettings: [],
  ManageSystem: ["ManageAppSettings", "ManageAccessControl"],
};

function getAllDependencies(permission: Permission): Permission[] {
  const direct = PermissionDependencies[permission] ?? [];
  const indirect = direct.flatMap(getAllDependencies);
  return Array.from(new Set([...direct, ...indirect]));
}

function removeDependents(
  selected: Permission[],
  removed: Permission
): Permission[] {
  const dependents = Object.entries(PermissionDependencies)
    .filter(([, deps]) => deps.includes(removed))
    .map(([perm]) => perm as Permission);

  let updated = selected.filter((p) => p !== removed);
  for (const dep of dependents) {
    if (updated.includes(dep)) {
      updated = removeDependents(updated, dep);
    }
  }
  return updated;
}

export function togglePermission(
  current: Permission[],
  permission: Permission,
  checked: boolean
): Permission[] {
  if (checked) {
    const deps = getAllDependencies(permission);
    return Array.from(new Set([...current, permission, ...deps]));
  }
  return removeDependents(current, permission);
}

export type PermissionGuard =
  | Permission
  | { any: Permission[] }
  | { all: Permission[] };
