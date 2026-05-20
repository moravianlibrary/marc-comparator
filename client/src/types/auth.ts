import type { Permission } from "./permission";

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  first_name: string;
  last_name: string;
  password: string;
}

export interface UserResponse {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  roles: Array<{ id: number; name: string }>;
}

export interface MeResponse extends UserResponse {
  permissions: Permission[];
}
