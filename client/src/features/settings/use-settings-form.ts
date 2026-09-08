import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect } from 'react';
import {
  type DefaultValues,
  type FieldValues,
  type Resolver,
  type SubmitHandler,
  useForm,
} from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import type { ZodType } from 'zod';

interface UseSettingsFormOptions<T extends FieldValues> {
  schema: ZodType<T>;
  defaultValues: DefaultValues<T>;
  onFormRef: (ref: { submit: () => void; reset: () => void }) => void;
  onDirtyChange: (dirty: boolean) => void;
  onSubmit: (data: T) => void;
}

export function useSettingsForm<T extends FieldValues>({
  schema,
  defaultValues,
  onFormRef,
  onDirtyChange,
  onSubmit,
}: UseSettingsFormOptions<T>) {
  const { t } = useTranslation();

  const form = useForm<T>({
    // zod's inferred schema output and react-hook-form's Resolver<T> do not unify
    // through the generic T, so the resolver has to be cast. The `as Resolver<T>` on
    // the result is what keeps the form itself type-checked.
    // biome-ignore lint/suspicious/noExplicitAny: see comment above
    resolver: zodResolver(schema as any) as Resolver<T>,
    defaultValues,
    // Track refetched server data as the new baseline: after a save the
    // query is invalidated and the saved values become the defaults, so
    // isDirty stays correct (including reverting a field to its old value).
    // keepDirtyValues preserves in-progress edits when a background
    // refetch lands mid-edit.
    values: defaultValues as T,
    resetOptions: { keepDirtyValues: true },
  });

  useEffect(() => {
    onFormRef({
      // Surface validation failures - without the invalid handler a submit
      // that fails validation on a field with no rendered input (or no
      // visible error) silently does nothing.
      submit: () =>
        form.handleSubmit(onSubmit as SubmitHandler<T>, () =>
          toast.error(t('common:validation-failed')),
        )(),
      reset: () => form.reset(defaultValues),
    });
  }, [form, onSubmit, defaultValues, onFormRef, t]);

  useEffect(() => {
    onDirtyChange(form.formState.isDirty);
  }, [form.formState.isDirty, onDirtyChange]);

  return form;
}
