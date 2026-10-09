import { Plus, Trash2 } from 'lucide-react';
import { useMemo } from 'react';
import { useFieldArray } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import type { AuthorityLinkingSettings } from '@/types/settings';
import { AuthorityLinkersHelp, LinkingDecisionHelp, MarcXmlDumpLinkerHelp } from './help-content';
import { HelpDialog } from './help-dialog';
import { type AuthorityLinkingSettingsFormValues, authorityLinkingSettingsSchema } from './schemas';
import { useSettingsForm } from './use-settings-form';
import { EXCELLENT_MATCH, MATCH_SCALE_MAX, MODERATE_MATCH } from '../records/score';

interface Props {
  data: AuthorityLinkingSettings;
  onDirtyChange: (dirty: boolean) => void;
  onFormRef: (ref: { submit: () => void; reset: () => void }) => void;
  onSubmit: (data: AuthorityLinkingSettings) => void;
}

export function AuthorityLinkingSettingsForm({ data, onDirtyChange, onFormRef, onSubmit }: Props) {
  const { t } = useTranslation('settings');

  const defaultValues = useMemo<AuthorityLinkingSettingsFormValues>(
    () => ({
      'knihovny-cz': data['knihovny-cz'] ?? {
        api_url: 'https://www.knihovny.cz/api/v1',
        minimum_confidence: MODERATE_MATCH,
        mappings: [{ base: '', id_template: '', pattern: '', is_target: false }],
      },
      'marcxml-dump': data['marcxml-dump'] ?? {
        dump_url: 'https://aleph.nkp.cz/data/skc.xml.gz',
        target_base: 'SKC',
        system_number_tag: '998',
        system_number_subfield: 'a',
        system_number_pattern: 'doc_number=(\\d+)',
        system_number_padding: 9,
        identifier_minimum_confidence: 0,
        title_minimum_confidence: 7.0,
        candidate_limit: 10,
      },
      confident_threshold: data.confident_threshold ?? EXCELLENT_MATCH,
      candidate_margin: data.candidate_margin ?? 1.5,
    }),
    [data],
  );

  const form = useSettingsForm({
    schema: authorityLinkingSettingsSchema,
    defaultValues,
    onFormRef,
    onDirtyChange,
    onSubmit,
  });

  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: 'knihovny-cz.mappings',
  });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <Card>
          <CardHeader className="flex flex-row items-center gap-2">
            <CardTitle className="text-base">{t('authority-linkers.decision.title')}</CardTitle>
            <HelpDialog titleKey="authority-linkers.decision.title">
              <LinkingDecisionHelp />
            </HelpDialog>
          </CardHeader>
          <CardContent>
            <FormField
              control={form.control}
              name="confident_threshold"
              render={({ field }) => (
                <FormItem className="max-w-xs">
                  <FormLabel>{t('authority-linkers.decision.confident-threshold')}</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      max={MATCH_SCALE_MAX}
                      {...field}
                      onChange={e => field.onChange(Number(e.target.value))}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="candidate_margin"
              render={({ field }) => (
                <FormItem className="mt-4 max-w-xs">
                  <FormLabel>{t('authority-linkers.decision.candidate-margin')}</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      max={MATCH_SCALE_MAX}
                      {...field}
                      onChange={e => field.onChange(Number(e.target.value))}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center gap-2">
            <CardTitle className="text-base">{t('authority-linkers.knihovny-cz.title')}</CardTitle>
            <HelpDialog titleKey="authority-linkers.knihovny-cz.title">
              <AuthorityLinkersHelp />
            </HelpDialog>
          </CardHeader>
          <CardContent className="space-y-4">
            <FormField
              control={form.control}
              name="knihovny-cz.api_url"
              render={({ field }) => (
                <FormItem className="max-w-md">
                  <FormLabel>{t('authority-linkers.knihovny-cz.api-url')}</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="knihovny-cz.minimum_confidence"
              render={({ field }) => (
                <FormItem className="max-w-xs">
                  <FormLabel>{t('authority-linkers.knihovny-cz.minimum-confidence')}</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      max={MATCH_SCALE_MAX}
                      {...field}
                      onChange={e => field.onChange(Number(e.target.value))}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="space-y-2">
              <FormLabel>{t('authority-linkers.knihovny-cz.mappings')}</FormLabel>
              {fields.map((field, index) => (
                <div key={field.id} className="flex items-end gap-2">
                  <FormField
                    control={form.control}
                    name={`knihovny-cz.mappings.${index}.base`}
                    render={({ field }) => (
                      <FormItem className="flex-1">
                        <FormLabel className="text-xs">
                          {t('authority-linkers.knihovny-cz.mapping-base')}
                        </FormLabel>
                        <FormControl>
                          <Input {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name={`knihovny-cz.mappings.${index}.id_template`}
                    render={({ field }) => (
                      <FormItem className="flex-1">
                        <FormLabel className="text-xs">
                          {t('authority-linkers.knihovny-cz.mapping-id-template')}
                        </FormLabel>
                        <FormControl>
                          <Input {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name={`knihovny-cz.mappings.${index}.pattern`}
                    render={({ field }) => (
                      <FormItem className="flex-1">
                        <FormLabel className="text-xs">
                          {t('authority-linkers.knihovny-cz.mapping-pattern')}
                        </FormLabel>
                        <FormControl>
                          <Input {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name={`knihovny-cz.mappings.${index}.is_target`}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-xs">
                          {t('authority-linkers.knihovny-cz.mapping-is-target')}
                        </FormLabel>
                        <FormControl>
                          <div className="flex h-9 items-center">
                            <Switch checked={field.value} onCheckedChange={field.onChange} />
                          </div>
                        </FormControl>
                      </FormItem>
                    )}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => remove(index)}
                    disabled={fields.length <= 1}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => append({ base: '', id_template: '', pattern: '', is_target: false })}
              >
                <Plus className="mr-2 h-4 w-4" />
                {t('authority-linkers.knihovny-cz.add-mapping')}
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center gap-2">
            <CardTitle className="text-base">{t('authority-linkers.marcxml-dump.title')}</CardTitle>
            <HelpDialog titleKey="authority-linkers.marcxml-dump.title">
              <MarcXmlDumpLinkerHelp />
            </HelpDialog>
          </CardHeader>
          <CardContent className="space-y-4">
            <FormField
              control={form.control}
              name="marcxml-dump.dump_url"
              render={({ field }) => (
                <FormItem className="max-w-md">
                  <FormLabel>{t('authority-linkers.marcxml-dump.dump-url')}</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="marcxml-dump.target_base"
              render={({ field }) => (
                <FormItem className="max-w-xs">
                  <FormLabel>{t('authority-linkers.marcxml-dump.target-base')}</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <div className="flex flex-wrap gap-2">
              <FormField
                control={form.control}
                name="marcxml-dump.system_number_tag"
                render={({ field }) => (
                  <FormItem className="w-24">
                    <FormLabel>{t('authority-linkers.marcxml-dump.system-number-tag')}</FormLabel>
                    <FormControl>
                      <Input className="font-mono" maxLength={3} {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="marcxml-dump.system_number_subfield"
                render={({ field }) => (
                  <FormItem className="w-24">
                    <FormLabel>
                      {t('authority-linkers.marcxml-dump.system-number-subfield')}
                    </FormLabel>
                    <FormControl>
                      <Input className="font-mono" maxLength={1} {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="marcxml-dump.system_number_pattern"
                render={({ field }) => (
                  <FormItem className="min-w-52 flex-1">
                    <FormLabel>
                      {t('authority-linkers.marcxml-dump.system-number-pattern')}
                    </FormLabel>
                    <FormControl>
                      <Input
                        className="font-mono"
                        name={field.name}
                        ref={field.ref}
                        onBlur={field.onBlur}
                        value={field.value ?? ''}
                        onChange={e =>
                          field.onChange(e.target.value === '' ? null : e.target.value)
                        }
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="marcxml-dump.system_number_padding"
                render={({ field }) => (
                  <FormItem className="w-28">
                    <FormLabel>
                      {t('authority-linkers.marcxml-dump.system-number-padding')}
                    </FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min="0"
                        max="16"
                        {...field}
                        onChange={e => field.onChange(Number(e.target.value))}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            <FormField
              control={form.control}
              name="marcxml-dump.identifier_minimum_confidence"
              render={({ field }) => (
                <FormItem className="max-w-xs">
                  <FormLabel>
                    {t('authority-linkers.marcxml-dump.identifier-minimum-confidence')}
                  </FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      max={MATCH_SCALE_MAX}
                      {...field}
                      onChange={e => field.onChange(Number(e.target.value))}
                    />
                  </FormControl>
                  <FormDescription>
                    {t('authority-linkers.marcxml-dump.identifier-minimum-confidence-help')}
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="marcxml-dump.title_minimum_confidence"
              render={({ field }) => (
                <FormItem className="max-w-xs">
                  <FormLabel>
                    {t('authority-linkers.marcxml-dump.title-minimum-confidence')}
                  </FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      max={MATCH_SCALE_MAX}
                      {...field}
                      onChange={e => field.onChange(Number(e.target.value))}
                    />
                  </FormControl>
                  <FormDescription>
                    {t('authority-linkers.marcxml-dump.title-minimum-confidence-help')}
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="marcxml-dump.candidate_limit"
              render={({ field }) => (
                <FormItem className="max-w-xs">
                  <FormLabel>{t('authority-linkers.marcxml-dump.candidate-limit')}</FormLabel>
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
          </CardContent>
        </Card>
      </form>
    </Form>
  );
}
