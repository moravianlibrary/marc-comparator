import { useState } from "react";
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
}

let notificationListeners: Array<(n: NotificationEntry) => void> = [];

export function addNotification(entry: Omit<NotificationEntry, "id" | "read">) {
  const notification: NotificationEntry = {
    ...entry,
    id: crypto.randomUUID(),
    read: false,
  };
  notificationListeners.forEach((fn) => fn(notification));
}

export function useNotificationStore() {
  const [notifications, setNotifications] = useState<NotificationEntry[]>([]);

  useState(() => {
    const listener = (n: NotificationEntry) => {
      setNotifications((prev) => [n, ...prev].slice(0, 100));
    };
    notificationListeners.push(listener);
    return () => {
      notificationListeners = notificationListeners.filter(
        (fn) => fn !== listener
      );
    };
  });

  const markAllRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  const clear = () => {
    setNotifications([]);
  };

  const unreadCount = notifications.filter((n) => !n.read).length;

  return { notifications, unreadCount, markAllRead, clear };
}

export function ToastHistory() {
  const { t } = useTranslation();
  const { notifications, unreadCount, markAllRead, clear } =
    useNotificationStore();

  return (
    <Sheet onOpenChange={(open) => open && markAllRead()}>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon" className="relative">
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
          <div className="flex items-center justify-between">
            <SheetTitle>{t("common:toast-history.title")}</SheetTitle>
            {notifications.length > 0 && (
              <Button variant="ghost" size="sm" onClick={clear}>
                {t("common:toast-history.clear")}
              </Button>
            )}
          </div>
        </SheetHeader>
        <ScrollArea className="h-[calc(100vh-8rem)] mt-4">
          {notifications.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              {t("common:toast-history.empty")}
            </p>
          ) : (
            <div className="space-y-3">
              {notifications.map((n) => (
                <div
                  key={n.id}
                  className="rounded-md border p-3 text-sm space-y-1"
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
