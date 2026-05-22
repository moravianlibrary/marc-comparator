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
}

export interface TaskSettings {
  progress_update_interval: number;
}

export interface KnihovnyCZBaseMapping {
  base: string;
  id_template: string;
  pattern: string;
  is_target: boolean;
}

export interface KnihovnyCZLinkerConfig {
  api_url: string;
  mappings: KnihovnyCZBaseMapping[];
}

export interface AuthorityLinkingSettings {
  "knihovny-cz": KnihovnyCZLinkerConfig | null;
}

export interface ComparatorConfig {
  ollama_url: string;
  llm_enabled: boolean;
  nonstandard_llm_enabled: boolean;
  valid_threshold: number;
  warning_threshold: number;
}

export interface ComparisonSettings {
  comparator: ComparatorConfig | null;
}

export interface KrameriusLinksValidatorConfig {
  url_to_pid_pattern: string;
  link_text_pattern: string;
  kramerius_host: string;
  solr_cloud: boolean;
}

export interface ValidationSettings {
  "kramerius-links": KrameriusLinksValidatorConfig | null;
}

export const AuthorityLinker = {
  KnihovnyCz: "knihovny-cz",
} as const;

export type AuthorityLinker =
  (typeof AuthorityLinker)[keyof typeof AuthorityLinker];

export const Validator = {
  KrameriusLinks: "kramerius-links",
} as const;

export type Validator = (typeof Validator)[keyof typeof Validator];

export interface ProcessRecordsSettings {
  target_bases: string[];
  authority_linkers: AuthorityLinker[];
  validators: Validator[];
}

export interface PeriodicTaskConfig {
  enabled: boolean;
  interval_hours: number;
}

export interface MaintenanceSettings {
  task_cleanup: PeriodicTaskConfig;
  task_cleanup_max_age_days: number;
  sector_compaction: PeriodicTaskConfig;
}

export type SettingsScope =
  | "catalog"
  | "tasks"
  | "authority-linkers"
  | "comparators"
  | "validators"
  | "process-records"
  | "maintenance";

export interface SystemInfo {
  system_version: string;
  system_commit: string;
  uptime_seconds: number;
  available_bases: string[];
  enabled_authority_linkers: Array<{ name: string; target_bases: string[] }>;
  enabled_validators: string[];
}
