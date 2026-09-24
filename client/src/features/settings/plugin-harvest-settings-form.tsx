import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Database, Loader2 } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useFormContext } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Form, FormControl, FormField, FormItem, FormLabel } from '@/components/ui/form';
import { Progress } from '@/components/ui/progress';
import { Switch } from '@/components/ui/switch';
import { useInvalidateTasks } from '@/hooks/use-invalidate-tasks';
import apiClient from '@/lib/api-client';
import type { HarvestPluginStatus } from '@/types/harvest';
import type { PluginHarvestSettings } from '@/types/settings';
import { CronField } from './cron-field';
import { isTaskInFlight } from '../tasks/task-status';
import { PluginHarvestHelp } from './help-content';
import { HelpDialog } from './help-dialog';
import { type PluginHarvestSettingsFormValues, pluginHarvestSettingsSchema } from './schemas';
import { useHarvestPlugins } from './use-harvest-plugins';
import { useSettingsForm } from './use-settings-form';

interface Props {
  data: PluginHarvestSettings;
  onDirtyChange: (dirty: boolean) => void;
  onFormRef: (ref: { submit: () => void; reset: () => void }) => void;
  onSubmit: (data: PluginHarvestSettings) => void;
}

export function PluginHarvestSettingsForm({ data, onDirtyChange, onFormRef, onSubmit }: Props) {
  const { t } = useTranslation('settings');
  const { data: statuses } = useHarvestPlugins();

  // The server returns one entry per discovered plugin, so the form never
  // hardcodes which plugins exist.
  const defaultValues = useMemo<PluginHarvestSettings>(
    () => ({ plugins: data?.plugins ?? {} }),
    [data],
  );

  const form = useSettingsForm({
    schema: pluginHarvestSettingsSchema,
    defaultValues,
    onFormRef,
    onDirtyChange,
    onSubmit,
  });

  const names = useMemo(() => Object.keys(defaultValues.plugins).sort(), [defaultValues]);
  const statusByName = useMemo(
    () => new Map((statuses ?? []).map(status => [status.name, status])),
    [statuses],
  );

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <Card>
          <CardHeader className="flex flex-row items-center gap-2">
            <CardTitle className="text-base">{t('types.plugin-harvest')}</CardTitle>
            <HelpDialog titleKey="types.plugin-harvest">
              <PluginHarvestHelp />
            </HelpDialog>
          </CardHeader>
          <CardContent>
            <CardDescription>{t('plugin-harvest.description')}</CardDescription>
          </CardContent>
        </Card>

        {names.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t('plugin-harvest.no-plugins')}</p>
        ) : (
          names.map(name => (
            <PluginHarvestCard key={name} name={name} status={statusByName.get(name)} />
          ))
        )}
      </form>
    </Form>
  );
}

function PluginHarvestCard({ name, status }: { name: string; status?: HarvestPluginStatus }) {
  const { t } = useTranslation('settings');
  const form = useFormContext<PluginHarvestSettingsFormValues>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const invalidateTasks = useInvalidateTasks();
  const [confirmRebuild, setConfirmRebuild] = useState(false);

  const runMutation = useMutation({
    mutationFn: (fullRebuild: boolean) =>
      apiClient.post(`/harvest/plugins/${encodeURIComponent(name)}/run`, {
        full_rebuild: fullRebuild,
      }),
    onSuccess: () => {
      toast.success(t('plugin-harvest.started'));
      invalidateTasks();
      queryClient.invalidateQueries({ queryKey: ['harvest'] });
    },
    onError: () => {
      toast.error(t('common:error'));
    },
  });

  // Plugin display names already exist under their own settings scope; falling
  // back to the registry name keeps a newly added plugin usable without a
  // translation.
  const title = status ? t(`${status.scope}.${name}.title`, { defaultValue: name }) : name;
  const task = status?.current_task ?? null;
  const running = task !== null && isTaskInFlight(task);
  const percent = task?.progress != null ? Math.round(task.progress * 100) : null;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center gap-2">
        <Database className="h-5 w-5 text-muted-foreground" />
        <CardTitle className="text-base">{title}</CardTitle>
        {status && (
          <Badge variant={status.ready ? 'secondary' : 'outline'}>
            {t(status.ready ? 'plugin-harvest.ready' : 'plugin-harvest.not-ready')}
          </Badge>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {status && !status.ready && (
          <p className="text-sm text-muted-foreground">{t('plugin-harvest.fallback-note')}</p>
        )}

        <dl className="grid gap-x-6 gap-y-1 text-sm sm:grid-cols-[auto_1fr]">
          <dt className="text-muted-foreground">{t('plugin-harvest.last-harvest')}</dt>
          <dd>
            {status?.last_harvest_at
              ? new Date(status.last_harvest_at).toLocaleString('cs-CZ')
              : t('plugin-harvest.never')}
          </dd>
          <dt className="text-muted-foreground">{t('plugin-harvest.total-records')}</dt>
          <dd>
            {status?.total_records != null ? status.total_records.toLocaleString('cs-CZ') : '—'}
          </dd>
          <dt className="text-muted-foreground">{t('plugin-harvest.last-records')}</dt>
          <dd>{status?.records != null ? status.records.toLocaleString('cs-CZ') : '—'}</dd>
        </dl>

        <div className="max-w-md space-y-3">
          <FormField
            control={form.control}
            name={`plugins.${name}.enabled`}
            render={({ field }) => (
              <FormItem className="flex items-center gap-3 space-y-0">
                <FormControl>
                  <Switch checked={field.value} onCheckedChange={field.onChange} />
                </FormControl>
                <FormLabel>{t('plugin-harvest.enabled')}</FormLabel>
              </FormItem>
            )}
          />
          <CronField control={form.control} name={`plugins.${name}.cron`} />
        </div>

        {running && task && (
          <button
            type="button"
            className="flex w-full max-w-md cursor-pointer items-center gap-3 rounded-md p-1 -m-1 text-left hover:bg-accent"
            onClick={() => navigate(`/tasks?taskId=${task.task_id}`)}
          >
            <span className="text-sm text-muted-foreground">{t('plugin-harvest.running')}</span>
            <Progress value={percent} className="h-2 w-24" />
            {percent != null && <span className="text-xs text-muted-foreground">{percent}%</span>}
          </button>
        )}

        <div className="flex gap-3">
          <Button
            type="button"
            size="sm"
            disabled={running || runMutation.isPending}
            onClick={() => runMutation.mutate(false)}
          >
            {runMutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                {t('plugin-harvest.run')}
              </>
            ) : (
              t('plugin-harvest.run')
            )}
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={running || runMutation.isPending}
            onClick={() => setConfirmRebuild(true)}
          >
            {t('plugin-harvest.full-rebuild')}
          </Button>
        </div>
      </CardContent>

      <AlertDialog open={confirmRebuild} onOpenChange={setConfirmRebuild}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('plugin-harvest.full-rebuild')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('plugin-harvest.full-rebuild-warning', { plugin: title })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('common:cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                setConfirmRebuild(false);
                runMutation.mutate(true);
              }}
            >
              {t('plugin-harvest.full-rebuild')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  );
}
