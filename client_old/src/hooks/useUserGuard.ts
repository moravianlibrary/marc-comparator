import type { Me } from "../models/api/responses/users";
import type { UserGuard } from "../app/userGuards";

/**
 * Evaluates a guard against the current user.
 * `null` guard → allowed.
 */
export function useUserGuard(
    guard: UserGuard | null | undefined,
    user: Me | null | undefined
): boolean {
    if (guard == null) return true;
    return guard(user);
}
