import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';

interface SettingsActionsProps {
  isDirty: boolean;
  isSaving: boolean;
  onSave: () => void;
  onDiscard: () => void;
}

export function SettingsActions({ isDirty, isSaving, onSave, onDiscard }: SettingsActionsProps) {
  const { t } = useTranslation();

  return (
    <div className="flex items-center gap-4">
      <Button onClick={onSave} disabled={!isDirty || isSaving}>
        {t('common:save')}
      </Button>
      <Button variant="outline" onClick={onDiscard} disabled={!isDirty}>
        {t('common:discard')}
      </Button>
    </div>
  );
}
