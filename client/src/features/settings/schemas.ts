import { z } from "zod";

export const catalogClientSchema = z.object({
  base: z.string().min(1),
  host: z.url(),
  endpoint: z.string().min(1),
  timeout: z.number().int().min(1).max(300),
  total_retry: z.number().int().min(0).max(20),
  retry_backoff_factor: z.number().int().min(0).max(10),
  system_number_pattern: z.string().min(1),
  oai_sets: z.array(z.string().min(1)).min(1),
  oai_identifier_template: z.string().min(1),
});

export const catalogSettingsSchema = z.object({
  clients: z.array(catalogClientSchema).min(1),
  kramerius_client_urls: z.record(z.string(), z.string()).default({}),
});

export type CatalogSettingsFormValues = z.infer<typeof catalogSettingsSchema>;

export const taskSettingsSchema = z.object({
  progress_update_interval: z.number().int().min(1),
  commit_interval: z.number().int().min(1),
  analytics_rebuild_interval: z.number().int().min(0),
});

export type TaskSettingsFormValues = z.infer<typeof taskSettingsSchema>;

export const knihovnyCZMappingSchema = z.object({
  base: z.string().min(1),
  id_template: z.string().min(1),
  pattern: z.string().min(1),
  is_target: z.boolean(),
});

export const knihovnyCZLinkerConfigSchema = z.object({
  api_url: z.url(),
  mappings: z.array(knihovnyCZMappingSchema).min(1),
});

export const authorityLinkingSettingsSchema = z.object({
  "knihovny-cz": knihovnyCZLinkerConfigSchema.nullable(),
});

export type AuthorityLinkingSettingsFormValues = z.infer<
  typeof authorityLinkingSettingsSchema
>;

export const comparatorConfigSchema = z.object({
  ollama_url: z.url(),
  llm_enabled: z.boolean(),
  nonstandard_llm_enabled: z.boolean(),
  valid_threshold: z.number().int().min(0).max(100),
  warning_threshold: z.number().int().min(0).max(100),
});

export const comparisonSettingsSchema = z.object({
  comparator: comparatorConfigSchema.nullable(),
});

export type ComparisonSettingsFormValues = z.infer<
  typeof comparisonSettingsSchema
>;

export const krameriusLinksConfigSchema = z.object({
  url_to_pid_pattern: z.string().min(1),
  url_to_pid_wrong_path_pattern: z.string().min(1),
  url_to_pid_fallback_pattern: z.string().min(1),
  link_text_pattern: z.string().min(1),
  kramerius_host: z.url(),
  kramerius_client_url: z.string().min(1),
  solr_cloud: z.boolean(),
});

export const validationSettingsSchema = z.object({
  "kramerius-links": krameriusLinksConfigSchema.nullable(),
});

export type ValidationSettingsFormValues = z.infer<
  typeof validationSettingsSchema
>;

export const processRecordsSettingsSchema = z.object({
  target_bases: z.array(z.string().min(1)).min(1),
  authority_linkers: z.array(z.enum(["knihovny-cz"])).min(1),
  validators: z.array(z.enum(["kramerius-links"])).min(1),
});

export type ProcessRecordsSettingsFormValues = z.infer<
  typeof processRecordsSettingsSchema
>;

export const periodicTaskConfigSchema = z.object({
  enabled: z.boolean(),
  interval_hours: z.number().int().min(1).max(720),
});

export const maintenanceSettingsSchema = z.object({
  task_cleanup: periodicTaskConfigSchema,
  task_cleanup_max_age_days: z.number().int().min(1).max(365),
  sector_compaction: periodicTaskConfigSchema,
});

export type MaintenanceSettingsFormValues = z.infer<typeof maintenanceSettingsSchema>;
