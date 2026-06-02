import { useEffect } from "react";
import {
  useForm,
  type DefaultValues,
  type FieldValues,
  type Resolver,
  type SubmitHandler,
} from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import type { ZodType } from "zod";

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
  const form = useForm<T>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(schema as any) as Resolver<T>,
    defaultValues,
  });

  useEffect(() => {
    onFormRef({
      submit: () => form.handleSubmit(onSubmit as SubmitHandler<T>)(),
      reset: () => form.reset(defaultValues),
    });
  }, [form, onSubmit, defaultValues, onFormRef]);

  useEffect(() => {
    onDirtyChange(form.formState.isDirty);
  }, [form.formState.isDirty, onDirtyChange]);

  return form;
}
