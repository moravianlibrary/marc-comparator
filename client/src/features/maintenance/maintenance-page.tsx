import { BarChart3, HardDrive, Scale, Search, Trash2, Unlock } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { SkeletonForm } from '@/components/skeletons/skeleton-form';
import { MaintenanceHelp } from '@/features/settings/help-content';
import { HelpDialog } from '@/features/settings/help-dialog';
import { MaintenanceSettingsForm } from '@/features/settings/maintenance-settings-form';
import { SettingsActions } from '@/features/settings/settings-actions';
import { useScopedSettings } from '@/features/settings/use-scoped-settings';
import { MaintenanceActionCard } from './maintenance-action-card';

export function MaintenancePage() {
  const { t } = useTranslation('maintenance');

  return (
    <div className="space-y-8 animate-fade-in">
      <h1 className="text-2xl font-semibold">{t('title')}</h1>

      <section className="space-y-4">
        <h2 className="text-lg font-medium">{t('sections.actions')}</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <MaintenanceActionCard
            icon={Trash2}
            titleKey="actions.delete-tasks.title"
            descriptionKey="actions.delete-tasks.description"
            endpoint="/maintenance/delete-tasks"
            showMaxAge
          />
          <MaintenanceActionCard
            icon={BarChart3}
            titleKey="actions.refresh-analytics.title"
            descriptionKey="actions.refresh-analytics.description"
            endpoint="/maintenance/refresh-analytics"
          />
          <MaintenanceActionCard
            icon={Unlock}
            titleKey="actions.cleanup-stale-locks.title"
            descriptionKey="actions.cleanup-stale-locks.description"
            endpoint="/maintenance/cleanup-stale-locks"
          />
          <MaintenanceActionCard
            icon={HardDrive}
            titleKey="actions.compact-sectors.title"
            descriptionKey="actions.compact-sectors.description"
            endpoint="/maintenance/compact-sectors"
          />
          <MaintenanceActionCard
            icon={Search}
            titleKey="actions.rebuild-search-vectors.title"
            descriptionKey="actions.rebuild-search-vectors.description"
            endpoint="/maintenance/rebuild-search-vectors"
          />
          <MaintenanceActionCard
            icon={Scale}
            titleKey="actions.rescore-comparisons.title"
            descriptionKey="actions.rescore-comparisons.description"
            endpoint="/maintenance/rescore-comparisons"
          />
        </div>
      </section>

      <MaintenanceSchedules />
    </div>
  );
}

function MaintenanceSchedules() {
  const { t } = useTranslation('maintenance');
  const { settings, isLoading, isDirty, isSaving, save, discard, formProps } =
    useScopedSettings('maintenance');

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-medium">{t('sections.schedules')}</h2>
          <HelpDialog titleKey="types.maintenance">
            <MaintenanceHelp />
          </HelpDialog>
        </div>
        <SettingsActions isDirty={isDirty} isSaving={isSaving} onSave={save} onDiscard={discard} />
      </div>
      {isLoading || !settings ? (
        <SkeletonForm fields={6} />
      ) : (
        <MaintenanceSettingsForm {...formProps} data={settings} />
      )}
    </section>
  );
}
