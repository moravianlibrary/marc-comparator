import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/api-client";
import type { SystemInfo } from "@/types/settings";

export function useSystemInfo(enabled = true) {
  return useQuery<SystemInfo>({
    queryKey: ["system", "info"],
    queryFn: () =>
      apiClient.get<SystemInfo>("/system/info").then((r) => r.data),
    enabled,
  });
}

export function useAvailableBases() {
  const { data } = useSystemInfo();
  return data?.available_bases ?? [];
}
