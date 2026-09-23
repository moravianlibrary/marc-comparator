import type { Control, FieldPath, FieldValues } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { Badge } from '@/components/ui/badge';
import { FormControl, FormField, FormItem, FormLabel } from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { CRON_PRESETS, describeCron } from '@/lib/cron';

interface CronFieldProps<T extends FieldValues> {
  control: Control<T>;
  name: FieldPath<T>;
  label?: string;
}

/**
 * The schedule field shared by every periodic job.
 *
 * A cron expression is precise but unreadable at a glance, so the field reads
 * itself back in words and offers the handful of schedules these jobs are
 * actually set to. An expression it cannot phrase is left unphrased rather
 * than guessed at.
 */
export function CronField<T extends FieldValues>({ control, name, label }: CronFieldProps<T>) {
  const { t } = useTranslation('settings');

  return (
    <FormField
      control={control}
      name={name}
      render={({ field, fieldState }) => {
        const value = typeof field.value === 'string' ? field.value : '';
        const described = describeCron(value);

        return (
          <FormItem>
            <FormLabel>{label ?? t('cron.label')}</FormLabel>
            <FormControl>
              <Input className="max-w-xs font-mono" placeholder="0 2 * * *" {...field} />
            </FormControl>
            <div className="flex flex-wrap items-center gap-1.5">
              {CRON_PRESETS.map(preset => (
                <Badge
                  key={preset.key}
                  variant={value.trim() === preset.expression ? 'default' : 'outline'}
                  className="cursor-pointer font-normal"
                  onClick={() => field.onChange(preset.expression)}
                >
                  {t(`cron.preset.${preset.key}`)}
                </Badge>
              ))}
            </div>
            {described && !fieldState.error && (
              <p className="text-xs text-muted-foreground">
                {t(`cron.describe.${described.key}`, {
                  ...described.values,
                  ...(described.values.day ? { day: t(`cron.${described.values.day}`) } : {}),
                })}
              </p>
            )}
            {/* The zod message is a code rather than a sentence, so the wording
                stays in the locale files with everything else. */}
            {fieldState.error && (
              <p className="text-xs font-medium text-destructive">{t('cron.invalid')}</p>
            )}
          </FormItem>
        );
      }}
    />
  );
}
