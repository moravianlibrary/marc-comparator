import type { RoleSummary } from "./role";

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  roles: RoleSummary[];
}
