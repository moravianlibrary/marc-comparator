import type { RoleSummary } from './role';

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  roles: RoleSummary[];
}

/**
 * The account scheduled jobs run as (periodic sync, maintenance). Mirrors
 * SYSTEM_USER_ID in app/entities/user.py.
 */
export const SYSTEM_USER_ID = '00000000-0000-0000-0000-000000000001';
