import type { ReactElement } from "react";
import { useHasAccess } from "../../hooks/useAuth";
import type { EnforcedPermission } from "../../models/ui/permissions";

export const AccessGuard = ({
    permission,
    children,
}: {
    permission?: EnforcedPermission;
    children: React.ReactNode;
}): ReactElement | null => {
    const { hasAccess } = useHasAccess();

    if (!permission || hasAccess(permission)) return <>{children}</>;

    return null;
};

export default AccessGuard;
