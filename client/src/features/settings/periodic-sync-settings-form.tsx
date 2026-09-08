import { useMemo } from 'react';
import { useFieldArray } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
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
import { useSystemInfo } from '@/hooks/use-system-info';
import type { PeriodicSyncSettings } from '@/types/settings';
import { periodicSyncSettingsSchema } from './schemas';
import { useSettingsForm } from './use-settings-form';

interface Props {
  data: PeriodicSyncSettings;
  onDirtyChange: (dirty: boolean) => void;
  onFormRef: (ref: { submit: () => void; reset: () => void }) => void;
  onSubmit: (data: PeriodicSyncSettings) => void;
}

export function PeriodicSyncSettingsForm({ data, onDirtyChange, onFormRef, onSubmit }: Props) {
  const { t } = useTranslation('settings');
  const { data: systemInfo } = useSystemInfo();

  // Merge the configured catalog bases with any saved per-base schedule so
  // every base is shown; unsaved ones default to disabled.
  const defaultValues = useMemo<PeriodicSyncSettings>(() => {
    const configured = systemInfo?.configured_bases ?? [];
    const existing = new Map((data?.bases ?? []).map(b => [b.base, b]));
    return {
      bases: configured.map(
        base => existing.get(base) ?? { base, enabled: false, interval_hours: 24 },
      ),
    };
  }, [data, systemInfo]);

  const form = useSettingsForm({
    schema: periodicSyncSettingsSchema,
    defaultValues,
    onFormRef,
    onDirtyChange,
    onSubmit,
  });

  const { fields } = useFieldArray({ control: form.control, name: 'bases' });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t('types.periodic-sync')}</CardTitle>
          </CardHeader>
          <CardContent className="max-w-md space-y-6">
            {fields.length === 0 ? (
              <p className="text-sm text-muted-foreground">{t('periodic-sync.no-bases')}</p>
            ) : (
              fields.map((field, index) => (
                <div key={field.id} className="space-y-3">
                  <h3 className="text-sm font-medium">{field.base}</h3>
                  <FormField
                    control={form.control}
                    name={`bases.${index}.enabled`}
                    render={({ field: f }) => (
                      <FormItem className="flex items-center gap-3 space-y-0">
                        <FormControl>
                          <Switch checked={f.value} onCheckedChange={f.onChange} />
                        </FormControl>
                        <FormLabel>{t('periodic-sync.enabled')}</FormLabel>
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name={`bases.${index}.interval_hours`}
                    render={({ field: f }) => (
                      <FormItem>
                        <FormLabel>{t('periodic-sync.interval-hours')}</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            {...f}
                            onChange={e => f.onChange(Number(e.target.value))}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </form>
    </Form>
  );
}
