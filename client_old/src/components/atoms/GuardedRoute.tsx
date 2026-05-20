import type { ReactElement } from "react";
import type { Me } from "../../models/api/responses/users";
import type { UserGuard } from "../../app/userGuards";
import { useUserGuard } from "../../hooks/useUserGuard";
import AccessDeniedPage from "../../pages/AccessDeniedPage";

export default function GuardedRoute({
    guard,
    user,
    element,
}: {
    guard: UserGuard | null | undefined;
    user: Me | null | undefined;
    element: ReactElement;
}): ReactElement {
    const allowed = useUserGuard(guard, user);
    if (!allowed) return <AccessDeniedPage />;
    return element;
}
