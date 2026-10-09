import { HardDrive, type LucideIcon, TimerReset, Trash2 } from 'lucide-react';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import type { MaintenanceSettings } from '@/types/settings';
import { CronField } from './cron-field';
import { maintenanceSettingsSchema } from './schemas';
import { useSettingsForm } from './use-settings-form';

interface Props {
  data: MaintenanceSettings;
  onDirtyChange: (dirty: boolean) => void;
  onFormRef: (ref: { submit: () => void; reset: () => void }) => void;
  onSubmit: (data: MaintenanceSettings) => void;
}

export function MaintenanceSettingsForm({ data, onDirtyChange, onFormRef, onSubmit }: Props) {
  const { t } = useTranslation('settings');

  const form = useSettingsForm({
    schema: maintenanceSettingsSchema,
    defaultValues: data,
    onFormRef,
    onDirtyChange,
    onSubmit,
  });

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        className="grid gap-4 md:grid-cols-2 lg:grid-cols-3"
      >
        <ScheduleCard
          icon={Trash2}
          titleKey="maintenance.task-cleanup.title"
          descriptionKey="maintenance.task-cleanup.description"
        >
          <FormField
            control={form.control}
            name="task_cleanup.enabled"
            render={({ field }) => (
              <FormItem className="flex items-center gap-3 space-y-0">
                <FormControl>
                  <Switch checked={field.value} onCheckedChange={field.onChange} />
                </FormControl>
                <FormLabel>{t('maintenance.enabled')}</FormLabel>
              </FormItem>
            )}
          />

          <CronField control={form.control} name="task_cleanup.cron" />

          <FormField
            control={form.control}
            name="task_cleanup_max_age_days"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('maintenance.max-age-days')}</FormLabel>
                <FormControl>
                  <Input
                    type="number"
                    {...field}
                    onChange={e => field.onChange(Number(e.target.value))}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </ScheduleCard>

        <ScheduleCard
          icon={HardDrive}
          titleKey="maintenance.sector-compaction.title"
          descriptionKey="maintenance.sector-compaction.description"
        >
          <FormField
            control={form.control}
            name="sector_compaction.enabled"
            render={({ field }) => (
              <FormItem className="flex items-center gap-3 space-y-0">
                <FormControl>
                  <Switch checked={field.value} onCheckedChange={field.onChange} />
                </FormControl>
                <FormLabel>{t('maintenance.enabled')}</FormLabel>
              </FormItem>
            )}
          />

          <CronField control={form.control} name="sector_compaction.cron" />
        </ScheduleCard>

        <ScheduleCard
          icon={TimerReset}
          titleKey="maintenance.orphan-reaper.title"
          descriptionKey="maintenance.orphan-reaper.description"
        >
          <FormField
            control={form.control}
            name="orphan_reaper.enabled"
            render={({ field }) => (
              <FormItem className="flex items-center gap-3 space-y-0">
                <FormControl>
                  <Switch checked={field.value} onCheckedChange={field.onChange} />
                </FormControl>
                <FormLabel>{t('maintenance.enabled')}</FormLabel>
              </FormItem>
            )}
          />

          <CronField control={form.control} name="orphan_reaper.cron" />
        </ScheduleCard>
      </form>
    </Form>
  );
}

interface ScheduleCardProps {
  icon: LucideIcon;
  titleKey: string;
  descriptionKey: string;
  children: ReactNode;
}

/** One scheduled job, laid out like the action cards it sits beside. */
function ScheduleCard({ icon: Icon, titleKey, descriptionKey, children }: ScheduleCardProps) {
  const { t } = useTranslation('settings');

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Icon className="h-5 w-5 text-muted-foreground" />
          <CardTitle className="text-base">{t(titleKey)}</CardTitle>
        </div>
        <CardDescription>{t(descriptionKey)}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">{children}</CardContent>
    </Card>
  );
}
