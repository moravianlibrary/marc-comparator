import type { Permission } from "./permission";

export interface Role {
  id: number;
  name: string;
  permissions: Permission[];
  immutable: boolean;
  protected: boolean;
}

export interface RoleSummary {
  id: number;
  name: string;
}

export interface EditRoleRequest {
  name: string;
  permissions: Permission[];
}
