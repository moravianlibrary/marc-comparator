import { AuthorityLinker, Validator } from '@/types/settings';
import { isValidCron } from '@/lib/cron';
import { z } from 'zod';

// looseObject: the server stores extra keys the form does not edit
// (e.g. the MARC parsing `context`) - a strict schema would silently strip
// them from the submitted payload and reset them to server defaults.
export const catalogClientSchema = z.looseObject({
  base: z.string().min(1),
  host: z.url(),
  endpoint: z.string().min(1),
  timeout: z.number().int().min(1).max(300),
  total_retry: z.number().int().min(0).max(20),
  retry_backoff_factor: z.number().int().min(0).max(10),
  system_number_pattern: z.string().min(1),
  // Edited as a comma-separated input; drop empty segments before validating.
  oai_sets: z.preprocess(
    v => (Array.isArray(v) ? v.map(s => String(s).trim()).filter(Boolean) : v),
    z.array(z.string().min(1)).min(1),
  ),
  oai_identifier_template: z.string().min(1),
});

export const catalogSettingsSchema = z.object({
  clients: z.array(catalogClientSchema).min(1),
  kramerius_client_urls: z.record(z.string(), z.string()).default({}),
});

export const taskSettingsSchema = z.object({
  progress_update_interval: z.number().int().min(1),
  commit_interval: z.number().int().min(1),
  analytics_rebuild_interval: z.number().int().min(0),
});

export const knihovnyCZMappingSchema = z.object({
  base: z.string().min(1),
  id_template: z.string().min(1),
  pattern: z.string().min(1),
  is_target: z.boolean(),
});

export const knihovnyCZLinkerConfigSchema = z.object({
  api_url: z.url(),
  minimum_confidence: z.number().min(0).max(1),
  mappings: z.array(knihovnyCZMappingSchema).min(1),
});

export const marcDumpLinkerConfigSchema = z.object({
  dump_url: z.url(),
  target_base: z.string().min(1),
  system_number_tag: z.string().length(3),
  system_number_subfield: z.string().length(1),
  system_number_pattern: z.string().nullable(),
  system_number_padding: z.number().int().min(0).max(16),
  identifier_minimum_confidence: z.number().min(0).max(1),
  title_minimum_confidence: z.number().min(0).max(1),
  candidate_limit: z.number().int().min(1).max(100),
});

export const authorityLinkingSettingsSchema = z.object({
  'knihovny-cz': knihovnyCZLinkerConfigSchema.nullable(),
  'marcxml-dump': marcDumpLinkerConfigSchema.nullable(),
  confident_threshold: z.number().min(0).max(1),
});

export type AuthorityLinkingSettingsFormValues = z.infer<typeof authorityLinkingSettingsSchema>;

export const comparatorConfigSchema = z.object({
  ollama_url: z.url(),
  llm_enabled: z.boolean(),
  nonstandard_llm_enabled: z.boolean(),
  excellent_threshold: z.number().int().min(0).max(100),
  moderate_threshold: z.number().int().min(0).max(100),
});

export const comparisonSettingsSchema = z.object({
  comparator: comparatorConfigSchema.nullable(),
});

export type ComparisonSettingsFormValues = z.infer<typeof comparisonSettingsSchema>;

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
  'kramerius-links': krameriusLinksConfigSchema.nullable(),
});

export type ValidationSettingsFormValues = z.infer<typeof validationSettingsSchema>;

export const processRecordsSettingsSchema = z.object({
  target_bases: z.array(z.string().min(1)).min(1),
  authority_linkers: z.array(z.enum(Object.values(AuthorityLinker))).min(1),
  validators: z.array(z.enum(Object.values(Validator))).min(1),
});

// The backend validates the expression too and is the authority; this keeps a
// typo in the form instead of letting it reach a scheduler nobody is watching.
export const cronExpressionSchema = z
  .string()
  .trim()
  .refine(isValidCron, { message: 'invalid-cron' });

export const periodicTaskConfigSchema = z.object({
  enabled: z.boolean(),
  cron: cronExpressionSchema,
});

export const maintenanceSettingsSchema = z.object({
  task_cleanup: periodicTaskConfigSchema,
  task_cleanup_max_age_days: z.number().int().min(1).max(365),
  sector_compaction: periodicTaskConfigSchema,
  orphan_reaper: periodicTaskConfigSchema,
});

export const periodicSyncBaseConfigSchema = z.object({
  base: z.string(),
  enabled: z.boolean(),
  cron: cronExpressionSchema,
});

export const periodicProcessingConfigSchema = z.object({
  enabled: z.boolean(),
  cron: cronExpressionSchema,
});

export const periodicSyncSettingsSchema = z.object({
  bases: z.array(periodicSyncBaseConfigSchema),
  processing: periodicProcessingConfigSchema,
});

export const pluginHarvestScheduleSchema = z.object({
  enabled: z.boolean(),
  cron: cronExpressionSchema,
});

export const pluginHarvestSettingsSchema = z.object({
  plugins: z.record(z.string(), pluginHarvestScheduleSchema),
});

export type PluginHarvestSettingsFormValues = z.infer<typeof pluginHarvestSettingsSchema>;
