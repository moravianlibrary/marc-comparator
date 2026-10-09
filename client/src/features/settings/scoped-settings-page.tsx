import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { SkeletonForm } from '@/components/skeletons/skeleton-form';
import type { SettingsScope } from '@/types/settings';
import { SettingsActions } from './settings-actions';
import { useScopedSettings } from './use-scoped-settings';

type FormProps = ReturnType<typeof useScopedSettings>['formProps'];

interface ScopedSettingsPageProps {
  scope: SettingsScope;
  /** Renders the scope's form once its settings have loaded. */
  children: (formProps: FormProps) => ReactNode;
}

/** A page given over to a single settings scope: title, save bar, form. */
export function ScopedSettingsPage({ scope, children }: ScopedSettingsPageProps) {
  const { t } = useTranslation('settings');
  const { settings, isLoading, isDirty, isSaving, save, discard, formProps } =
    useScopedSettings(scope);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold">{t(`types.${scope}`)}</h1>
        <SettingsActions isDirty={isDirty} isSaving={isSaving} onSave={save} onDiscard={discard} />
      </div>
      {isLoading || !settings ? (
        <SkeletonForm fields={6} />
      ) : (
        <div className="animate-fade-in">{children(formProps)}</div>
      )}
    </div>
  );
}
