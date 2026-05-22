export const Permission = {
  ReadRecords: "ReadRecords",
  ReviewRecords: "ReviewRecords",
  ManageReviews: "ManageReviews",
  AddRecords: "AddRecords",
  SyncRecordsFromCatalog: "SyncRecordsFromCatalog",
  ProcessRecords: "ProcessRecords",
  RunPartialRecordTasks: "RunPartialRecordTasks",
  ManageTasks: "ManageTasks",
  ManageAllTasks: "ManageAllTasks",
  ManageAccessControl: "ManageAccessControl",
  ManageAppSettings: "ManageAppSettings",
  ManageTaskSettings: "ManageTaskSettings",
} as const;

export type Permission = (typeof Permission)[keyof typeof Permission];

export const PermissionDependencies: Record<Permission, Permission[]> = {
  ReadRecords: [],
  ReviewRecords: ["ReadRecords"],
  ManageReviews: ["ReviewRecords"],
  AddRecords: ["ReadRecords"],
  SyncRecordsFromCatalog: ["ReadRecords", "AddRecords", "ManageTasks"],
  ProcessRecords: ["ReadRecords"],
  RunPartialRecordTasks: ["ReadRecords"],
  ManageTasks: ["ProcessRecords", "RunPartialRecordTasks"],
  ManageAllTasks: ["ManageTasks"],
  ManageTaskSettings: ["ManageTasks"],
  ManageAccessControl: [],
  ManageAppSettings: [],
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
