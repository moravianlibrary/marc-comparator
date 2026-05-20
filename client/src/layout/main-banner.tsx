import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { LogOut, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import apiClient from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { useGetMe, useLogout } from "@/hooks/use-auth";
import { MenuPanel } from "./menu-panel";
import { TaskProgress } from "./task-progress";
import { ToastHistory } from "./toast-history";
import type { Task } from "@/types/task";

export function MainBanner() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { data: me } = useGetMe();
  const logout = useLogout();
  const { theme, setTheme } = useTheme();

  const { data: tasksData } = useQuery<{ items: Task[] }>({
    queryKey: ["tasks", "running"],
    queryFn: () =>
      apiClient
        .post<{ items: Task[] }>("/tasks/search-own", {
          filters: { status: ["Started"] },
          page: 1,
          page_size: 20,
        })
        .then((r) => r.data),
    refetchInterval: 5000,
  });

  const runningTasks = tasksData?.items ?? [];

  return (
    <header className="border-b bg-background px-6 py-2 flex items-center gap-4">
      <Button
        variant="ghost"
        className="font-semibold text-lg p-0 h-auto hover:bg-transparent"
        onClick={() => navigate("/")}
      >
        {t("common:app-name")}
      </Button>

      <MenuPanel />

      <div className="flex-1" />

      <TaskProgress runningTasks={runningTasks} />
      <ToastHistory />

      <Button
        variant="ghost"
        size="icon"
        onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      >
        <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
        <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
        <span className="sr-only">Toggle theme</span>
      </Button>

      {me && (
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">
            {me.first_name} {me.last_name}
          </span>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => logout.mutate()}
          >
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      )}
    </header>
  );
}
