import { useEffect, useState } from "react";
import { Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import apiClient from "@/lib/api-client";
import { useGetMe } from "@/hooks/use-auth";
import { useWsEvents } from "@/hooks/use-ws-events";
import { Skeleton } from "@/components/ui/skeleton";
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

  const [redirecting, setRedirecting] = useState(false);

  useEffect(() => {
    if (isHealthError) {
      setRedirecting(true);
      const redirect = window.location.pathname + window.location.search;
      window.location.href =
        "/service-unavailable?redirect=" + encodeURIComponent(redirect);
    } else if (!isHealthLoading && !isMeLoading && (isMeError || !me)) {
      setRedirecting(true);
      const currentPath = window.location.pathname;
      window.location.href =
        "/login?redirect=" + encodeURIComponent(currentPath);
    }
  }, [isHealthError, isHealthLoading, isMeLoading, isMeError, me]);

  if (isHealthLoading || isMeLoading) {
    return (
      <div className="flex h-screen flex-col">
        {/* Banner skeleton */}
        <div className="flex h-14 items-center gap-4 border-b px-4">
          <Skeleton className="h-8 w-8 rounded" />
          <Skeleton className="h-4 w-32" />
          <div className="flex-1" />
          <Skeleton className="h-8 w-8 rounded-full" />
        </div>
        {/* Content skeleton */}
        <div className="flex-1 p-6 space-y-4">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-4 w-96" />
          <div className="grid grid-cols-3 gap-4 pt-4">
            <Skeleton className="h-48 rounded-lg" />
            <Skeleton className="h-48 rounded-lg" />
            <Skeleton className="h-48 rounded-lg" />
          </div>
        </div>
      </div>
    );
  }

  if (redirecting || isHealthError || isMeError || !me) {
    return null;
  }

  return (
    <div className="flex min-h-screen flex-col animate-fade-in">
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
