import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import apiClient from '@/lib/api-client';
import type { SettingsScope } from '@/types/settings';

export const SETTINGS_ENDPOINTS: Record<SettingsScope, string> = {
  catalog: '/settings/system/catalog',
  tasks: '/settings/system/tasks',
  'authority-linkers': '/settings/record-tools/authority-linkers',
  comparators: '/settings/record-tools/comparators',
  validators: '/settings/record-tools/validators',
  'process-records': '/settings/record-tools/process-records',
  maintenance: '/settings/system/maintenance',
  'periodic-sync': '/settings/system/periodic-sync',
  'plugin-harvest': '/settings/system/plugin-harvest',
};

interface FormRef {
  submit: () => void;
  reset: () => void;
}

/**
 * Load, edit and save one settings scope.
 *
 * The settings page switches between scopes; the maintenance, schedule and
 * plugin pages each hold one. Both need the same load / dirty / save / discard
 * wiring around a form, so it lives here rather than in either page.
 */
export function useScopedSettings(scope: SettingsScope) {
  const { t } = useTranslation('settings');
  const queryClient = useQueryClient();
  const endpoint = SETTINGS_ENDPOINTS[scope];

  const [isDirty, setIsDirty] = useState(false);
  const formRef = useRef<FormRef | null>(null);
  const setFormRef = useCallback((ref: FormRef) => {
    formRef.current = ref;
  }, []);

  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings', scope],
    queryFn: () => apiClient.get(endpoint).then(r => r.data),
  });

  const saveMutation = useMutation({
    mutationFn: (data: unknown) => apiClient.post(endpoint, data),
    onSuccess: () => {
      // The refetched data becomes the form's new baseline (values prop in
      // useSettingsForm), which flips isDirty back to false — no manual
      // setIsDirty here, it would desync from the form's own dirty state.
      queryClient.invalidateQueries({ queryKey: ['settings', scope] });
      toast.success(t('common:saved'));
    },
    onError: () => {
      toast.error(t('common:save-failed'));
    },
  });

  const discard = useCallback(() => {
    formRef.current?.reset();
    setIsDirty(false);
  }, []);

  return {
    settings,
    isLoading,
    isDirty,
    isSaving: saveMutation.isPending,
    save: () => formRef.current?.submit(),
    discard,
    formProps: {
      data: settings,
      onDirtyChange: setIsDirty,
      onFormRef: setFormRef,
      onSubmit: (data: unknown) => saveMutation.mutate(data),
    },
  };
}
