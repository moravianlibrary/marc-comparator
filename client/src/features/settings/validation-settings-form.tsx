import { useMemo } from 'react';
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
import type { ValidationSettings } from '@/types/settings';
import { ValidatorsHelp } from './help-content';
import { HelpDialog } from './help-dialog';
import { type ValidationSettingsFormValues, validationSettingsSchema } from './schemas';
import { useSettingsForm } from './use-settings-form';

interface Props {
  data: ValidationSettings;
  onDirtyChange: (dirty: boolean) => void;
  onFormRef: (ref: { submit: () => void; reset: () => void }) => void;
  onSubmit: (data: ValidationSettings) => void;
}

export function ValidationSettingsForm({ data, onDirtyChange, onFormRef, onSubmit }: Props) {
  const { t } = useTranslation('settings');

  const defaultValues = useMemo<ValidationSettingsFormValues>(
    () => ({
      'kramerius-links': data['kramerius-links'] ?? {
        own_host_pattern: '',
        canonical_path_pattern: '',
        non_canonical_path_pattern: '',
        link_text_pattern: '',
        link_text: '',
        kramerius_host: '',
        kramerius_client_url: '',
        solr_cloud: true,
      },
    }),
    [data],
  );

  const form = useSettingsForm({
    schema: validationSettingsSchema,
    defaultValues,
    onFormRef,
    onDirtyChange,
    onSubmit,
  });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <Card>
          <CardHeader className="flex flex-row items-center gap-2">
            <CardTitle className="text-base">{t('validators.kramerius-links.title')}</CardTitle>
            <HelpDialog titleKey="validators.kramerius-links.title">
              <ValidatorsHelp />
            </HelpDialog>
          </CardHeader>
          <CardContent className="max-w-xl space-y-4">
            <FormField
              control={form.control}
              name="kramerius-links.own_host_pattern"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('validators.kramerius-links.own-host-pattern')}</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="kramerius-links.canonical_path_pattern"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('validators.kramerius-links.canonical-path-pattern')}</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="kramerius-links.non_canonical_path_pattern"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    {t('validators.kramerius-links.non-canonical-path-pattern')}
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
              name="kramerius-links.link_text_pattern"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('validators.kramerius-links.link-text-pattern')}</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="kramerius-links.link_text"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('validators.kramerius-links.link-text')}</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="kramerius-links.kramerius_host"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('validators.kramerius-links.kramerius-host')}</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="kramerius-links.kramerius_client_url"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('validators.kramerius-links.kramerius-client-url')}</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="https://www.digitalniknihovna.cz/mzk/uuid/{pid}"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="kramerius-links.solr_cloud"
              render={({ field }) => (
                <FormItem className="flex items-center justify-between rounded-md border p-3">
                  <FormLabel>{t('validators.kramerius-links.solr-cloud')}</FormLabel>
                  <FormControl>
                    <Switch checked={field.value} onCheckedChange={field.onChange} />
                  </FormControl>
                </FormItem>
              )}
            />
          </CardContent>
        </Card>
      </form>
    </Form>
  );
}
