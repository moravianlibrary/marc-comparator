import {
  useQueryStates,
  parseAsString,
  parseAsInteger,
  parseAsStringLiteral,
  parseAsArrayOf,
  parseAsFloat,
} from "nuqs";
import type { RecordFilter, RecordTab, SearchRecordsRequest } from "./types";

const tabValues = ["plots", "table", "carousel", "addition"] as const;
const sortByValues = [
  "id",
  "base",
  "system_number",
  "latest_sync",
  "updated_at",
  "comparison_score",
] as const;
const sortOrderValues = ["asc", "desc"] as const;

export function useRecordFilters() {
  const [filters, setFilters] = useQueryStates(
    {
      tab: parseAsStringLiteral(tabValues).withDefault("plots"),
      page: parseAsInteger.withDefault(1),
      pageSize: parseAsInteger.withDefault(25),
      sortBy: parseAsStringLiteral(sortByValues).withDefault("latest_sync"),
      sortOrder: parseAsStringLiteral(sortOrderValues).withDefault("desc"),
      search: parseAsString.withDefault(""),

      bases: parseAsArrayOf(parseAsString).withDefault([]),
      typeOfRecord: parseAsArrayOf(parseAsString).withDefault([]),
      bibliographicLevel: parseAsArrayOf(parseAsString).withDefault([]),

      reviewStatuses: parseAsArrayOf(parseAsString).withDefault([]),
      deleted: parseAsString.withDefault(""),
      processed: parseAsString.withDefault(""),

      authorityLinkLinkers: parseAsArrayOf(parseAsString).withDefault([]),
      authorityLinkBases: parseAsArrayOf(parseAsString).withDefault([]),
      comparisonBases: parseAsArrayOf(parseAsString).withDefault([]),
      matchQualities: parseAsArrayOf(parseAsString).withDefault([]),
      fieldExplanations: parseAsArrayOf(parseAsString).withDefault([]),
      validators: parseAsArrayOf(parseAsString).withDefault([]),
      validationStatuses: parseAsArrayOf(parseAsString).withDefault([]),
      validationTargetTags: parseAsArrayOf(parseAsString).withDefault([]),
      validationReasons: parseAsArrayOf(parseAsString).withDefault([]),

      scoreMin: parseAsFloat.withDefault(0),
      scoreMax: parseAsFloat.withDefault(1),

      recordId: parseAsString.withDefault(""),
      recordIndex: parseAsInteger.withDefault(0),
      carouselView: parseAsString.withDefault(""),
    },
    { history: "replace", shallow: true },
  );

  function setTab(tab: RecordTab) {
    setFilters({ tab });
  }

  function setPage(page: number) {
    setFilters({ page });
  }

  function setSearch(search: string) {
    setFilters({ search, page: 1 });
  }

  function setScoreRange(from: number, to: number) {
    setFilters({ scoreMin: from, scoreMax: to, page: 1 });
  }

  function toggleArrayFilter(field: keyof typeof filters, value: string) {
    const current = filters[field];
    if (!Array.isArray(current)) return;
    const next = current.includes(value)
      ? current.filter((v: string) => v !== value)
      : [...current, value];
    setFilters({ [field]: next, page: 1 } as any);
  }

  function clearFilters() {
    setFilters({
      bases: [],
      typeOfRecord: [],
      bibliographicLevel: [],
      reviewStatuses: [],
      deleted: "",
      processed: "",
      authorityLinkLinkers: [],
      authorityLinkBases: [],
      comparisonBases: [],
      matchQualities: [],
      fieldExplanations: [],
      validators: [],
      validationStatuses: [],
      validationTargetTags: [],
      validationReasons: [],
      scoreMin: 0,
      scoreMax: 1,
      search: "",
      page: 1,
      recordId: "",
      recordIndex: 0,
      carouselView: "",
    });
  }

  function buildRecordFilter(): RecordFilter {
    const f: RecordFilter = {};
    if (filters.search) f.text_query = filters.search;
    if (filters.bases.length) f.bases = filters.bases;
    if (filters.typeOfRecord.length) f.type_of_record = filters.typeOfRecord;
    if (filters.bibliographicLevel.length)
      f.bibliographic_level = filters.bibliographicLevel;
    if (filters.deleted === "true") f.deleted = true;
    if (filters.deleted === "false") f.deleted = false;
    if (filters.processed === "true") f.processed = true;
    if (filters.processed === "false") f.processed = false;
    if (filters.reviewStatuses.length)
      f.review_statuses = filters.reviewStatuses;
    if (filters.authorityLinkLinkers.length)
      f.authority_link_linkers = filters.authorityLinkLinkers;
    if (filters.authorityLinkBases.length)
      f.authority_link_bases = filters.authorityLinkBases;
    if (filters.comparisonBases.length)
      f.comparison_bases = filters.comparisonBases;
    if (filters.matchQualities.length)
      f.match_qualities = filters.matchQualities;
    if (filters.fieldExplanations.length)
      f.field_explanations = filters.fieldExplanations;
    if (filters.validators.length) f.validators = filters.validators;
    if (filters.validationStatuses.length)
      f.validation_statuses = filters.validationStatuses;
    if (filters.validationTargetTags.length)
      f.validation_target_tags = filters.validationTargetTags;
    if (filters.validationReasons.length)
      f.validation_reasons = filters.validationReasons;
    if (filters.scoreMin > 0) f.score_min = filters.scoreMin;
    if (filters.scoreMax < 1) f.score_max = filters.scoreMax;
    if (filters.recordId) f.record_ids = [filters.recordId];
    return f;
  }

  function buildSearchPayload(): SearchRecordsRequest {
    return {
      filters: buildRecordFilter(),
      page: filters.page,
      page_size: filters.pageSize,
      sort_by: filters.sortBy,
      sort_order: filters.sortOrder,
    };
  }

  return {
    filters,
    setFilters,
    setTab,
    setPage,
    setSearch,
    setScoreRange,
    toggleArrayFilter,
    clearFilters,
    buildRecordFilter,
    buildSearchPayload,
  };
}
