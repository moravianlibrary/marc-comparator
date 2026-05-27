import { useSyncExternalStore } from "react";
import { useNavigate } from "react-router-dom";
import { Bell } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";

export interface NotificationEntry {
  id: string;
  title: string;
  description?: string;
  variant: "default" | "success" | "error";
  timestamp: string;
  read: boolean;
  taskId?: string;
}

let notifications: NotificationEntry[] = [];
let storeListeners = new Set<() => void>();

function emitChange() {
  storeListeners.forEach((fn) => fn());
}

function subscribe(listener: () => void) {
  storeListeners.add(listener);
  return () => storeListeners.delete(listener);
}

function getSnapshot() {
  return notifications;
}

export function addNotification(entry: Omit<NotificationEntry, "id" | "read">) {
  // Deduplicate by taskId + variant (e.g. same task success arriving via WS and mutation)
  if (entry.taskId) {
    const duplicate = notifications.find(
      (n) => n.taskId === entry.taskId && n.variant === entry.variant,
    );
    if (duplicate) return;
  }
  notifications = [
    { ...entry, id: crypto.randomUUID(), read: false },
    ...notifications,
  ].slice(0, 100);
  emitChange();
}

function markAllRead() {
  notifications = notifications.map((n) => ({ ...n, read: true }));
  emitChange();
}

export function useNotificationStore() {
  const items = useSyncExternalStore(subscribe, getSnapshot);
  const unreadCount = items.filter((n) => !n.read).length;
  return { notifications: items, unreadCount, markAllRead };
}

export function ToastHistory() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { notifications, unreadCount, markAllRead } =
    useNotificationStore();

  return (
    <Sheet onOpenChange={(open) => open && markAllRead()}>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon" className="relative" title={t("common:toast-history.title")}>
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <Badge
              variant="destructive"
              className="absolute -top-1 -right-1 h-5 w-5 p-0 flex items-center justify-center text-xs"
            >
              {unreadCount}
            </Badge>
          )}
        </Button>
      </SheetTrigger>
      <SheetContent>
        <SheetHeader>
          <SheetTitle>{t("common:toast-history.title")}</SheetTitle>
        </SheetHeader>
        <ScrollArea className="h-[calc(100vh-8rem)] mt-4">
          {notifications.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              {t("common:toast-history.empty")}
            </p>
          ) : (
            <div className="space-y-3 px-4">
              {notifications.map((n) => (
                <div
                  key={n.id}
                  className={`rounded-md border p-3 text-sm space-y-1 ${n.taskId ? "cursor-pointer hover:bg-accent" : ""}`}
                  onClick={n.taskId ? () => navigate(`/tasks?taskId=${n.taskId}`) : undefined}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{n.title}</span>
                    <span className="text-xs text-muted-foreground">
                      {new Date(n.timestamp).toLocaleTimeString("cs-CZ")}
                    </span>
                  </div>
                  {n.description && (
                    <p className="text-muted-foreground">{n.description}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}
