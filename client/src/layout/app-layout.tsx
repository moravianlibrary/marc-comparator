import { Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import apiClient from "@/lib/api-client";
import { useGetMe } from "@/hooks/use-auth";
import { useWsEvents } from "@/hooks/use-ws-events";
import { LockBanner } from "./lock-banner";
import { MainBanner } from "./main-banner";

export function AppLayout() {
  const { t } = useTranslation("common");
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
        <div className="text-muted-foreground">{t("loading")}</div>
      </div>
    );
  }

  if (isHealthError) {
    const redirect = window.location.pathname + window.location.search;
    window.location.href =
      "/service-unavailable?redirect=" + encodeURIComponent(redirect);
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
      <div className="sticky top-0 z-50">
        <LockBanner />
        <MainBanner />
      </div>
      <main className="flex-1 p-6">
        <Outlet />
      </main>
    </div>
  );
}
