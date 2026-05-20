import type { ReactElement } from "react";
import { useHasAccess } from "../../hooks/useAuth";
import type { EnforcedPermission } from "../../models/ui/permissions";

export const ProtectedRoute = ({
    permission,
    element,
}: {
    permission?: EnforcedPermission;
    element: ReactElement;
}): ReactElement | null => {
    const { hasAccess } = useHasAccess();

    if (!permission || hasAccess(permission)) return <>{element}</>;

    return null;
};

export default ProtectedRoute;
