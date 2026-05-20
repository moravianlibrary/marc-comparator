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
}

export interface KnihovnyCZLinkerConfig {
  api_url: string;
  mappings: KnihovnyCZBaseMapping[];
}

export interface AuthorityLinkingSettings {
  "knihovny-cz": KnihovnyCZLinkerConfig | null;
}

export interface IntiimComparatorConfig {
  ollama_url: string;
  llm_enabled: boolean;
  nonstandard_llm_enabled: boolean;
  valid_threshold: number;
  warning_threshold: number;
}

export interface ComparisonSettings {
  intiim: IntiimComparatorConfig | null;
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

export const Comparator = {
  Intiim: "intiim",
} as const;

export type Comparator = (typeof Comparator)[keyof typeof Comparator];

export const Validator = {
  KrameriusLinks: "kramerius-links",
} as const;

export type Validator = (typeof Validator)[keyof typeof Validator];

export interface ProcessRecordsSettings {
  target_bases: string[];
  authority_linkers: AuthorityLinker[];
  comparator: Comparator;
  validators: Validator[];
}

export type SettingsScope =
  | "catalog"
  | "tasks"
  | "authority-linkers"
  | "comparators"
  | "validators"
  | "process-records";

export interface SystemInfo {
  system_version: string;
  system_commit: string;
  uptime_seconds: number;
  available_bases: string[];
  enabled_authority_linkers: Array<{ name: string; target_bases: string[] }>;
  enabled_comparators: string[];
  enabled_validators: string[];
}
