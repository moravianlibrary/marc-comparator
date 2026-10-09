import { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { SkeletonForm } from '@/components/skeletons/skeleton-form';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { SettingsScope } from '@/types/settings';
import { AuthorityLinkingSettingsForm } from './authority-linking-settings-form';
import { CatalogSettingsForm } from './catalog-settings-form';
import { ComparisonSettingsForm } from './comparison-settings-form';
import { ProcessRecordsSettingsForm } from './process-records-settings-form';
import { SettingsActions } from './settings-actions';
import { TaskSettingsForm } from './task-settings-form';
import { useScopedSettings } from './use-scoped-settings';
import { ValidationSettingsForm } from './validation-settings-form';

// Maintenance, the record schedules and the plugin copies have pages of their
// own (see the menu); this page holds what configures the tools themselves.
const SETTINGS_SCOPES = [
  'catalog',
  'tasks',
  'authority-linkers',
  'comparators',
  'validators',
  'process-records',
] as const satisfies readonly SettingsScope[];

type PageScope = (typeof SETTINGS_SCOPES)[number];

export function SettingsPage() {
  const { t } = useTranslation('settings');

  const [activeScope, setActiveScope] = useState<PageScope>('catalog');
  const [pendingScope, setPendingScope] = useState<PageScope | null>(null);
  const { settings, isLoading, isDirty, isSaving, save, discard, formProps } =
    useScopedSettings(activeScope);

  const handleScopeChange = useCallback(
    (newScope: PageScope) => {
      if (isDirty) {
        setPendingScope(newScope);
      } else {
        setActiveScope(newScope);
      }
    },
    [isDirty],
  );

  const handleDiscardAndSwitch = useCallback(() => {
    if (pendingScope) {
      discard();
      setActiveScope(pendingScope);
      setPendingScope(null);
    }
  }, [pendingScope, discard]);

  function renderForm() {
    if (isLoading || !settings) {
      return <SkeletonForm fields={6} />;
    }

    const commonProps = { ...formProps, data: settings };

    let form: React.ReactNode;
    switch (activeScope) {
      case 'catalog':
        form = <CatalogSettingsForm {...commonProps} />;
        break;
      case 'tasks':
        form = <TaskSettingsForm {...commonProps} />;
        break;
      case 'authority-linkers':
        form = <AuthorityLinkingSettingsForm {...commonProps} />;
        break;
      case 'comparators':
        form = <ComparisonSettingsForm {...commonProps} />;
        break;
      case 'validators':
        form = <ValidationSettingsForm {...commonProps} />;
        break;
      case 'process-records':
        form = <ProcessRecordsSettingsForm {...commonProps} />;
        break;
    }
    return <div className="animate-fade-in">{form}</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <h1 className="text-2xl font-semibold">{t('title')}</h1>
      </div>

      <div className="flex items-center gap-4">
        <Select value={activeScope} onValueChange={v => handleScopeChange(v as PageScope)}>
          <SelectTrigger className="w-[320px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {SETTINGS_SCOPES.map(scope => (
              <SelectItem key={scope} value={scope}>
                {t(`types.${scope}`)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <SettingsActions isDirty={isDirty} isSaving={isSaving} onSave={save} onDiscard={discard} />
      </div>

      {renderForm()}

      <AlertDialog
        open={pendingScope !== null}
        onOpenChange={open => !open && setPendingScope(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('unsaved-warning')}</AlertDialogTitle>
            <AlertDialogDescription>{t('unsaved-warning')}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('common:cancel')}</AlertDialogCancel>
            <AlertDialogAction onClick={handleDiscardAndSwitch}>
              {t('common:discard')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
