export interface AlephOAIConfig {
  base: string;
  host: string;
  endpoint: string;
  timeout: number;
  total_retry: number;
  retry_backoff_factor: number;
  system_number_pattern: string;
  oai_sets: string[];
  oai_identifier_template: string;
}

export interface CatalogSettings {
  clients: AlephOAIConfig[];
  kramerius_client_urls: Record<string, string>;
}

export interface TaskSettings {
  progress_update_interval: number;
  commit_interval: number;
  analytics_rebuild_interval: number;
}

export interface KnihovnyCZBaseMapping {
  base: string;
  id_template: string;
  pattern: string;
  is_target: boolean;
}

export interface KnihovnyCZLinkerConfig {
  api_url: string;
  /** Lowest comparator score this linker will report at all. */
  minimum_confidence: number;
  mappings: KnihovnyCZBaseMapping[];
}

export interface MarcXmlDumpLinkerConfig {
  dump_url: string;
  target_base: string;
  /** Which field of the dump carries a record's own system number. */
  system_number_tag: string;
  system_number_subfield: string;
  /** Extracts the number from that field; null when it holds nothing else. */
  system_number_pattern: string | null;
  /** Left-pad the number to this width; 0 stores it verbatim. */
  system_number_padding: number;
  /** Lowest comparator score this linker will report at all. */
  minimum_confidence: number;
  /** How many retrieved records are compared per catalog record. */
  candidate_limit: number;
}

export interface AuthorityLinkingSettings {
  'knihovny-cz': KnihovnyCZLinkerConfig | null;
  'marcxml-dump': MarcXmlDumpLinkerConfig | null;
  /** Confidence at which linking stops consulting further linkers. */
  confident_threshold: number;
}

export interface ComparatorConfig {
  ollama_url: string;
  llm_enabled: boolean;
  nonstandard_llm_enabled: boolean;
  excellent_threshold: number;
  moderate_threshold: number;
}

export interface ComparisonSettings {
  comparator: ComparatorConfig | null;
}

export interface KrameriusLinksValidatorConfig {
  url_to_pid_pattern: string;
  url_to_pid_wrong_path_pattern: string;
  url_to_pid_fallback_pattern: string;
  link_text_pattern: string;
  kramerius_host: string;
  kramerius_client_url: string;
  solr_cloud: boolean;
}

export interface ValidationSettings {
  'kramerius-links': KrameriusLinksValidatorConfig | null;
}

export const AuthorityLinker = {
  KnihovnyCz: 'knihovny-cz',
  MarcXmlDump: 'marcxml-dump',
} as const;

export type AuthorityLinker = (typeof AuthorityLinker)[keyof typeof AuthorityLinker];

export const Validator = {
  KrameriusLinks: 'kramerius-links',
} as const;

export type Validator = (typeof Validator)[keyof typeof Validator];

export interface ProcessRecordsSettings {
  target_bases: string[];
  authority_linkers: AuthorityLinker[];
  validators: Validator[];
}

export interface PeriodicTaskConfig {
  enabled: boolean;
  /** Five-field cron expression, e.g. `0 2 * * *`. */
  cron: string;
}

export interface MaintenanceSettings {
  task_cleanup: PeriodicTaskConfig;
  task_cleanup_max_age_days: number;
  sector_compaction: PeriodicTaskConfig;
  orphan_reaper: PeriodicTaskConfig;
}

export interface PeriodicSyncBaseConfig {
  base: string;
  enabled: boolean;
  /** Five-field cron expression, e.g. `0 2 * * *`. */
  cron: string;
}

export interface PeriodicProcessingConfig {
  enabled: boolean;
  /** Five-field cron expression, e.g. `0 2 * * *`. */
  cron: string;
}

export interface PeriodicSyncSettings {
  bases: PeriodicSyncBaseConfig[];
  processing: PeriodicProcessingConfig;
}

export interface PluginHarvestSchedule {
  enabled: boolean;
  /** Five-field cron expression, e.g. `0 2 * * *`. */
  cron: string;
}

/** Keyed by plugin name; the server fills in a default for every discovered plugin. */
export interface PluginHarvestSettings {
  plugins: Record<string, PluginHarvestSchedule>;
}

export type SettingsScope =
  | 'catalog'
  | 'tasks'
  | 'authority-linkers'
  | 'comparators'
  | 'validators'
  | 'process-records'
  | 'maintenance'
  | 'periodic-sync'
  | 'plugin-harvest';

export interface SystemInfo {
  system_version: string;
  system_commit: string;
  uptime_seconds: number;
  configured_bases: string[];
  authority_bases: string[];
  enabled_authority_linkers: Array<{ name: string; target_bases: string[] }>;
  enabled_validators: string[];
  report_capable_validators: string[];
  report_capable_comparator: string | null;
  kramerius_client_urls: Record<string, string>;
}
