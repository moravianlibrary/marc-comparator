import type { ReactElement, ReactNode } from "react";
import type { Me } from "../../models/api/responses/users";
import type { UserGuard } from "../../app/userGuards";
import { useUserGuard } from "../../hooks/useUserGuard";

/** Hide nav entry when the guard fails. */
export default function NavGuard({
    guard,
    user,
    children,
}: {
    guard: UserGuard | null | undefined;
    user: Me | null | undefined;
    children: ReactNode;
}): ReactElement | null {
    const allowed = useUserGuard(guard, user);
    if (!allowed) return null;
    return <>{children}</>;
}
