// --- Search types ---

export interface RecordFilter {
  record_ids?: string[];
  text_query?: string;
  bases?: string[];
  type_of_record?: string[];
  bibliographic_level?: string[];
  deleted?: boolean;
  processed?: boolean;
  review_statuses?: string[];
  authority_link_linkers?: string[];
  authority_link_bases?: string[];
  comparison_bases?: string[];
  match_qualities?: string[];
  field_explanations?: string[];
  validators?: string[];
  validation_statuses?: string[];
  validation_target_tags?: string[];
  validation_reasons?: string[];
  score_min?: number;
  score_max?: number;
}

export interface AuthorityLinkSummary {
  linker: string;
  base: string;
  authority_record_id: string;
}

export interface ComparisonSummary {
  comparator: string;
  base: string;
  other_record_id: string;
  overall_score: number;
  match_quality: "Excellent" | "Moderate" | "Poor";
}

export interface ValidationSummary {
  validator: string;
  target_tag: string;
  status: "Valid" | "ForReview" | "Invalid" | "AdditionalInfo";
}

export interface RecordSummary {
  id: string;
  base: string;
  system_number: string;
  title: string | null;
  authors: string[];
  type_of_record: string | null;
  bibliographic_level: string | null;
  state: string[];
  authority_links: AuthorityLinkSummary[];
  comparisons: ComparisonSummary[];
  validations: ValidationSummary[];
  latest_sync: string | null;
  latest_transaction: string | null;
  processed_at: string | null;
}

export interface SearchRecordsRequest {
  filters?: RecordFilter;
  page?: number;
  page_size?: number;
  sort_by?: "id" | "base" | "system_number" | "latest_sync" | "updated_at" | "comparison_score";
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
  value_a: string | null;
  value_b: string | null;
  score: number;
  explanation: string | null;
  details: string | null;
}

export interface FieldComparisonResult {
  tag: string;
  value_a: string | null;
  value_b: string | null;
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
  target: { tag: string; codes: string[] | null; field_index: number | null };
  status: string;
  reason: string | null;
  params: Record<string, string> | null;
}

// --- Comparison/validation detail responses (from per-record endpoints) ---

export interface ComparisonDetail {
  comparator: string;
  base: string;
  other_record_id: string;
  result: ComparisonResult;
}

export interface ValidationDetail {
  id: number;
  validator: string;
  result: ValidationResult;
}

// --- Review types ---

export interface ReviewDetail {
  id: string;
  record_id: string;
  aspect_name: string;
  note: string | null;
  reviewed_by: string;
  reviewer_name: string | null;
  reviewed_at: string;
  status: "current" | "outdated" | "superseded";
}

export interface RecordReviewsResponse {
  current: ReviewDetail[];
  history: ReviewDetail[];
}

// --- Tab type ---

export type RecordTab = "plots" | "table" | "carousel" | "addition";

// --- Shared style constants ---

export const STATE_COLORS: Record<string, string> = {
  Active: "state-active",
  Deleted: "state-deleted",
  Unprocessed: "state-unprocessed",
  Processed: "state-processed",
  Reviewed: "state-reviewed",
  PartiallyReviewed: "state-partially-reviewed",
  Unreviewed: "state-unreviewed",
  ReviewNotNeeded: "state-review-not-needed",
};
