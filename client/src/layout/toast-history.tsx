import { Bell } from 'lucide-react';
import { useSyncExternalStore } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';

export interface NotificationEntry {
  id: string;
  title: string;
  description?: string;
  variant: 'default' | 'success' | 'error';
  timestamp: string;
  read: boolean;
  taskId?: string;
}

let notifications: NotificationEntry[] = [];
const storeListeners = new Set<() => void>();

function emitChange() {
  storeListeners.forEach(fn => {
    fn();
  });
}

function subscribe(listener: () => void) {
  storeListeners.add(listener);
  return () => storeListeners.delete(listener);
}

function getSnapshot() {
  return notifications;
}

export function addNotification(entry: Omit<NotificationEntry, 'id' | 'read'>) {
  // Deduplicate by taskId + variant (e.g. same task success arriving via WS and mutation)
  if (entry.taskId) {
    const duplicate = notifications.find(
      n => n.taskId === entry.taskId && n.variant === entry.variant,
    );
    if (duplicate) {
      return;
    }
  }
  notifications = [{ ...entry, id: crypto.randomUUID(), read: false }, ...notifications].slice(
    0,
    100,
  );
  emitChange();
}

function markAllRead() {
  notifications = notifications.map(n => ({ ...n, read: true }));
  emitChange();
}

export function useNotificationStore() {
  const items = useSyncExternalStore(subscribe, getSnapshot);
  const unreadCount = items.filter(n => !n.read).length;
  return { notifications: items, unreadCount, markAllRead };
}

export function ToastHistory() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { notifications, unreadCount, markAllRead } = useNotificationStore();

  return (
    <Sheet onOpenChange={open => open && markAllRead()}>
      <SheetTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative"
          title={t('common:toast-history.title')}
        >
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
          <SheetTitle>{t('common:toast-history.title')}</SheetTitle>
        </SheetHeader>
        <ScrollArea className="h-[calc(100vh-8rem)] mt-4">
          {notifications.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              {t('common:toast-history.empty')}
            </p>
          ) : (
            <div className="space-y-3 px-4">
              {notifications.map(n => {
                const openTask = n.taskId ? () => navigate(`/tasks?taskId=${n.taskId}`) : undefined;
                const className = `rounded-md border p-3 text-sm space-y-1 w-full text-left ${
                  openTask ? 'cursor-pointer hover:bg-accent' : ''
                }`;
                // Only notifications that link to a task are interactive, so only those
                // become buttons — a button around a non-linking row would lie to AT.
                const body = (
                  <>
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{n.title}</span>
                      <span className="text-xs text-muted-foreground">
                        {new Date(n.timestamp).toLocaleTimeString('cs-CZ')}
                      </span>
                    </div>
                    {n.description && <p className="text-muted-foreground">{n.description}</p>}
                  </>
                );
                return openTask ? (
                  <button type="button" key={n.id} className={className} onClick={openTask}>
                    {body}
                  </button>
                ) : (
                  <div key={n.id} className={className}>
                    {body}
                  </div>
                );
              })}
            </div>
          )}
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}
