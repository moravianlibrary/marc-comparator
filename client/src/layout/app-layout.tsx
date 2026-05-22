import { Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/api-client";
import { useGetMe } from "@/hooks/use-auth";
import { useWsEvents } from "@/hooks/use-ws-events";
import { LockBanner } from "./lock-banner";
import { MainBanner } from "./main-banner";

export function AppLayout() {
  const {
    isLoading: isHealthLoading,
    isError: isHealthError,
  } = useQuery({
    queryKey: ["health"],
    queryFn: () => apiClient.get("/system/health"),
    retry: 1,
  });

  const { data: me, isLoading: isMeLoading, isError: isMeError } = useGetMe();
  useWsEvents();

  if (isHealthLoading || isMeLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-muted-foreground">Načítání...</div>
      </div>
    );
  }

  if (isHealthError) {
    window.location.href = "/service-unavailable";
    return null;
  }

  if (isMeError || !me) {
    const currentPath = window.location.pathname;
    window.location.href =
      "/login?redirect=" + encodeURIComponent(currentPath);
    return null;
  }

  return (
    <div className="flex min-h-screen flex-col">
      <LockBanner />
      <MainBanner />
      <main className="flex-1 p-6">
        <Outlet />
      </main>
    </div>
  );
}
