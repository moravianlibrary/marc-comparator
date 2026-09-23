import { ArrowDown, ArrowUp } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Form, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { useSystemInfo } from '@/hooks/use-system-info';
import { AuthorityLinker, type ProcessRecordsSettings, Validator } from '@/types/settings';
import { ProcessRecordsHelp } from './help-content';
import { HelpDialog } from './help-dialog';
import { processRecordsSettingsSchema } from './schemas';
import { useSettingsForm } from './use-settings-form';

/** Move one entry of a list to another index, leaving the rest in order. */
function move<T>(items: T[], from: number, to: number): T[] {
  const next = [...items];
  const [moved] = next.splice(from, 1);
  if (moved === undefined) {
    return items;
  }
  next.splice(to, 0, moved);
  return next;
}

interface Props {
  data: ProcessRecordsSettings;
  onDirtyChange: (dirty: boolean) => void;
  onFormRef: (ref: { submit: () => void; reset: () => void }) => void;
  onSubmit: (data: ProcessRecordsSettings) => void;
}

export function ProcessRecordsSettingsForm({ data, onDirtyChange, onFormRef, onSubmit }: Props) {
  const { t } = useTranslation('settings');

  const { data: systemInfo } = useSystemInfo();

  const form = useSettingsForm({
    schema: processRecordsSettingsSchema,
    defaultValues: data,
    onFormRef,
    onDirtyChange,
    onSubmit,
  });

  const linkerTargetBases = [
    ...new Set(systemInfo?.enabled_authority_linkers.flatMap(l => l.target_bases) ?? []),
  ];

  const knownLinkers = Object.values(AuthorityLinker) as string[];
  const configuredLinkers = (systemInfo?.enabled_authority_linkers ?? [])
    .map(l => l.name)
    .filter((name): name is AuthorityLinker => knownLinkers.includes(name));

  const knownValidators = Object.values(Validator) as string[];
  const configuredValidators = (systemInfo?.enabled_validators ?? []).filter(
    (name): name is Validator => knownValidators.includes(name),
  );

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <Card>
          <CardHeader className="flex flex-row items-center gap-2">
            <CardTitle className="text-base">{t('types.process-records')}</CardTitle>
            <HelpDialog titleKey="types.process-records">
              <ProcessRecordsHelp />
            </HelpDialog>
          </CardHeader>
          <CardContent className="max-w-md space-y-4">
            <FormField
              control={form.control}
              name="target_bases"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('process-records.target-bases')}</FormLabel>
                  <div className="space-y-2">
                    {linkerTargetBases.map(base => (
                      <label key={base} className="flex items-center gap-2">
                        <Checkbox
                          checked={field.value.includes(base)}
                          onCheckedChange={checked => {
                            if (checked) {
                              field.onChange([...field.value, base]);
                            } else {
                              field.onChange(field.value.filter(b => b !== base));
                            }
                          }}
                        />
                        <span className="text-sm">{base}</span>
                      </label>
                    ))}
                  </div>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="authority_linkers"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('process-records.authority-linkers')}</FormLabel>
                  {/* Order is priority, not presentation: linking asks these in
                      turn and stops at the first confident enough answer. So the
                      selected ones are listed in the order they will be asked,
                      and the unselected ones after them. Configured linkers come
                      from the backend, so one this build cannot name is left out
                      rather than saved back as a value the schema rejects. */}
                  <p className="text-xs text-muted-foreground">
                    {t('process-records.authority-linkers-order')}
                  </p>
                  <div className="space-y-2">
                    {field.value
                      .filter(linker => configuredLinkers.includes(linker))
                      .map((linker, index, selected) => (
                        <div key={linker} className="flex items-center gap-2">
                          <span className="w-5 text-xs tabular-nums text-muted-foreground">
                            {index + 1}.
                          </span>
                          <Checkbox
                            checked
                            onCheckedChange={() =>
                              field.onChange(field.value.filter(v => v !== linker))
                            }
                          />
                          <span className="flex-1 text-sm">
                            {t(`authority-linkers.${linker}.title`, { defaultValue: linker })}
                          </span>
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7"
                            disabled={index === 0}
                            aria-label={t('process-records.move-up')}
                            onClick={() => field.onChange(move(selected, index, index - 1))}
                          >
                            <ArrowUp className="h-4 w-4" />
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7"
                            disabled={index === selected.length - 1}
                            aria-label={t('process-records.move-down')}
                            onClick={() => field.onChange(move(selected, index, index + 1))}
                          >
                            <ArrowDown className="h-4 w-4" />
                          </Button>
                        </div>
                      ))}
                    {configuredLinkers
                      .filter(linker => !field.value.includes(linker))
                      .map(linker => (
                        <label key={linker} className="flex items-center gap-2 pl-7">
                          <Checkbox
                            checked={false}
                            onCheckedChange={() => field.onChange([...field.value, linker])}
                          />
                          <span className="text-sm text-muted-foreground">
                            {t(`authority-linkers.${linker}.title`, { defaultValue: linker })}
                          </span>
                        </label>
                      ))}
                  </div>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="validators"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('process-records.validators')}</FormLabel>
                  <div className="space-y-2">
                    {/* Same contract as the linkers above: the backend names the
                        validators it has, and one this build cannot name is left
                        out rather than saved back as a value the schema rejects. */}
                    {configuredValidators.map(validator => (
                      <label key={validator} className="flex items-center gap-2">
                        <Checkbox
                          checked={field.value.includes(validator)}
                          onCheckedChange={checked => {
                            if (checked) {
                              field.onChange([...field.value, validator]);
                            } else {
                              field.onChange(field.value.filter(v => v !== validator));
                            }
                          }}
                        />
                        <span className="text-sm">
                          {t(`validators.${validator}.title`, { defaultValue: validator })}
                        </span>
                      </label>
                    ))}
                  </div>
                  <FormMessage />
                </FormItem>
              )}
            />
          </CardContent>
        </Card>
      </form>
    </Form>
  );
}
