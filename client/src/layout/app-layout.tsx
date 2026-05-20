import { Outlet } from "react-router-dom";
import { useGetMe } from "@/hooks/use-auth";
import { LockBanner } from "./lock-banner";
import { MainBanner } from "./main-banner";

export function AppLayout() {
  const { data: me, isLoading, isError } = useGetMe();

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-muted-foreground">Načítání...</div>
      </div>
    );
  }

  if (isError || !me) {
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
