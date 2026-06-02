import { useCallback } from "react";
import { useGetMe } from "./use-auth";
import type { Permission, PermissionGuard } from "@/types/permission";

export function useHasPermission() {
  const { data: me, isLoading } = useGetMe();

  const hasPermission = useCallback(
    (guard: PermissionGuard): boolean | undefined => {
      if (isLoading || !me) return undefined;

      if (typeof guard === "string") {
        return me.permissions.includes(guard);
      }
      if ("any" in guard) {
        return guard.any.some((p: Permission) => me.permissions.includes(p));
      }
      if ("all" in guard) {
        return guard.all.every((p: Permission) => me.permissions.includes(p));
      }
      return false;
    },
    [me, isLoading],
  );

  return { isLoading, hasPermission, me };
}
