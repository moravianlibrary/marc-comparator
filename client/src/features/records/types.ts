// --- Search types ---

export interface RecordFilter {
  text_query?: string;
  bases?: string[];
  type_of_record?: string[];
  bibliographic_level?: string[];
  hidden?: boolean;
  deleted?: boolean;
  processed?: boolean;
  authority_link_linkers?: string[];
  authority_link_bases?: string[];
  comparators?: string[];
  comparison_bases?: string[];
  match_qualities?: string[];
  field_explanations?: string[];
  validators?: string[];
  validation_statuses?: string[];
  validation_target_tags?: string[];
  score_min?: number;
  score_max?: number;
}

export interface RecordSummary {
  id: string;
  base: string;
  system_number: string;
  title: string | null;
  authors: string[];
  state: string[];
  authority_links_count: number;
  comparisons_count: number;
  validations_count: number;
  latest_sync: string | null;
  latest_transaction: string | null;
  processed_at: string | null;
}

export interface SearchRecordsRequest {
  filters?: RecordFilter;
  page?: number;
  page_size?: number;
  sort_by?: "id" | "base" | "system_number" | "latest_sync" | "updated_at";
  sort_order?: "asc" | "desc";
}

export interface SearchRecordsResponse {
  items: RecordSummary[];
  total: number;
  page: number;
  page_size: number;
}

// --- Facets types ---

export interface FacetBucket {
  key: string;
  count: number;
}

export interface FacetResult {
  field: string;
  buckets: FacetBucket[];
}

export interface HistogramBucket {
  min: number;
  max: number;
  count: number;
}

export interface HistogramResult {
  field: string;
  buckets: HistogramBucket[];
}

export interface FacetsResponse {
  facets: FacetResult[];
  histograms: HistogramResult[];
  total: number;
}

export interface FacetsPreviewEntry {
  target_value: string;
  facets: FacetResult[];
  histograms: HistogramResult[];
  total: number;
}

export interface FacetsPreviewResponse {
  target_field: string;
  previews: FacetsPreviewEntry[];
}

// --- MARC types (matches marcdantic MarcRecord JSON output) ---

export interface VariableField {
  ind1: string | null;
  ind2: string | null;
  subfields: Record<string, string[]>;
}

export interface MarcRecordData {
  leader: string;
  fixed_fields: Record<string, string>;
  variable_fields: Record<string, VariableField[]>;
}

// --- Comparison/validation detail types (from JSONB result columns) ---

export interface SubfieldComparisonResult {
  code: string;
  score: number;
  explanation: string | null;
  details: string | null;
}

export interface FieldComparisonResult {
  tag: string;
  score: number;
  explanation: string | null;
  details: string | null;
  subfield_results: SubfieldComparisonResult[] | null;
}

export interface ComparisonResult {
  overall_score: number;
  match_quality: string;
  summary: string | null;
  field_results: FieldComparisonResult[] | null;
}

export interface ValidationResult {
  target: { tag: string; codes: string[] | null };
  status: string;
  reason: string | null;
  details: string | null;
  hint: string | null;
}

// --- Tab type ---

export type RecordTab = "plots" | "table" | "carousel" | "addition";
