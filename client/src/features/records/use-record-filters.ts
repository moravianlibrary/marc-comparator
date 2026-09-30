import {
  parseAsArrayOf,
  parseAsFloat,
  parseAsInteger,
  parseAsString,
  parseAsStringLiteral,
  useQueryStates,
} from 'nuqs';
import { useEffect } from 'react';
import type { RecordFilter, RecordTab, SearchRecordsRequest } from './types';
import { MATCH_SCALE_MAX } from './score';

const tabValues = ['plots', 'table', 'carousel', 'addition'] as const;
const sortByValues = [
  'id',
  'base',
  'system_number',
  'latest_sync',
  'updated_at',
  'comparison_score',
] as const;
const sortOrderValues = ['asc', 'desc'] as const;

/** Filter keys whose value is a string array — the only ones toggleArrayFilter accepts.
 *  Listing a non-array key here is a compile error inside toggleArrayFilter. */
const ARRAY_FILTER_KEYS = [
  'bases',
  'typeOfRecord',
  'bibliographicLevel',
  'reviewStatuses',
  'authorityLinkLinkers',
  'authorityLinkBases',
  'linkOutcomes',
  'linkAgencies',
  'comparisonBases',
  'matchQualities',
  'fieldExplanations',
  'validators',
  'validationStatuses',
  'validationTargetTags',
  'validationReasons',
] as const;

export type ArrayFilterKey = (typeof ARRAY_FILTER_KEYS)[number];

/** Filter keys holding a tri-state string: '' (any), 'true' or 'false'. */
export type BoolFilterKey = 'deleted' | 'processed';

export function useRecordFilters() {
  const [filters, setFilters] = useQueryStates(
    {
      tab: parseAsStringLiteral(tabValues).withDefault('plots'),
      page: parseAsInteger.withDefault(1),
      pageSize: parseAsInteger.withDefault(Number(localStorage.getItem('records:pageSize')) || 25),
      sortBy: parseAsStringLiteral(sortByValues).withDefault('latest_sync'),
      sortOrder: parseAsStringLiteral(sortOrderValues).withDefault('desc'),
      search: parseAsString.withDefault(''),

      bases: parseAsArrayOf(parseAsString).withDefault([]),
      typeOfRecord: parseAsArrayOf(parseAsString).withDefault([]),
      bibliographicLevel: parseAsArrayOf(parseAsString).withDefault([]),

      reviewStatuses: parseAsArrayOf(parseAsString).withDefault([]),
      deleted: parseAsString.withDefault(''),
      processed: parseAsString.withDefault(''),

      authorityLinkLinkers: parseAsArrayOf(parseAsString).withDefault([]),
      authorityLinkBases: parseAsArrayOf(parseAsString).withDefault([]),
      linkOutcomes: parseAsArrayOf(parseAsString).withDefault([]),
      linkAgencies: parseAsArrayOf(parseAsString).withDefault([]),
      comparisonBases: parseAsArrayOf(parseAsString).withDefault([]),
      matchQualities: parseAsArrayOf(parseAsString).withDefault([]),
      fieldExplanations: parseAsArrayOf(parseAsString).withDefault([]),
      validators: parseAsArrayOf(parseAsString).withDefault([]),
      validationStatuses: parseAsArrayOf(parseAsString).withDefault([]),
      validationTargetTags: parseAsArrayOf(parseAsString).withDefault([]),
      validationReasons: parseAsArrayOf(parseAsString).withDefault([]),

      scoreMin: parseAsFloat.withDefault(0),
      scoreMax: parseAsFloat.withDefault(MATCH_SCALE_MAX),

      recordId: parseAsString.withDefault(''),
      recordIndex: parseAsInteger.withDefault(0),
      carouselView: parseAsString.withDefault(''),
    },
    { history: 'replace', shallow: true },
  );

  useEffect(() => {
    localStorage.setItem('records:pageSize', String(filters.pageSize));
  }, [filters.pageSize]);

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

  // A computed key widens the object literal to a string index signature, so the cast
  // is unavoidable — but it is to the real filter shape, not `any`, and `field` is
  // constrained by its type rather than checked with Array.isArray at runtime.
  function toggleArrayFilter(field: ArrayFilterKey, value: string) {
    const current = filters[field];
    const next = current.includes(value) ? current.filter(v => v !== value) : [...current, value];
    setFilters({ [field]: next, page: 1 } as Partial<typeof filters>);
  }

  function setBoolFilter(field: BoolFilterKey, value: string) {
    setFilters({ [field]: value, page: 1 } as Partial<typeof filters>);
  }

  function clearFilters() {
    setFilters({
      bases: [],
      typeOfRecord: [],
      bibliographicLevel: [],
      reviewStatuses: [],
      deleted: '',
      processed: '',
      authorityLinkLinkers: [],
      authorityLinkBases: [],
      linkOutcomes: [],
      linkAgencies: [],
      comparisonBases: [],
      matchQualities: [],
      fieldExplanations: [],
      validators: [],
      validationStatuses: [],
      validationTargetTags: [],
      validationReasons: [],
      scoreMin: 0,
      scoreMax: MATCH_SCALE_MAX,
      search: '',
      page: 1,
      recordId: '',
      recordIndex: 0,
      carouselView: '',
    });
  }

  function buildRecordFilter(): RecordFilter {
    const f: RecordFilter = {};
    if (filters.search) {
      f.text_query = filters.search;
    }
    if (filters.bases.length) {
      f.bases = filters.bases;
    }
    if (filters.typeOfRecord.length) {
      f.type_of_record = filters.typeOfRecord;
    }
    if (filters.bibliographicLevel.length) {
      f.bibliographic_level = filters.bibliographicLevel;
    }
    if (filters.deleted === 'true') {
      f.deleted = true;
    }
    if (filters.deleted === 'false') {
      f.deleted = false;
    }
    if (filters.processed === 'true') {
      f.processed = true;
    }
    if (filters.processed === 'false') {
      f.processed = false;
    }
    if (filters.reviewStatuses.length) {
      f.review_statuses = filters.reviewStatuses;
    }
    if (filters.authorityLinkLinkers.length) {
      f.authority_link_linkers = filters.authorityLinkLinkers;
    }
    if (filters.authorityLinkBases.length) {
      f.authority_link_bases = filters.authorityLinkBases;
    }
    if (filters.linkOutcomes.length) {
      f.link_outcomes = filters.linkOutcomes;
    }
    if (filters.linkAgencies.length) {
      f.link_agencies = filters.linkAgencies;
    }
    if (filters.comparisonBases.length) {
      f.comparison_bases = filters.comparisonBases;
    }
    if (filters.matchQualities.length) {
      f.match_qualities = filters.matchQualities;
    }
    if (filters.fieldExplanations.length) {
      f.field_explanations = filters.fieldExplanations;
    }
    if (filters.validators.length) {
      f.validators = filters.validators;
    }
    if (filters.validationStatuses.length) {
      f.validation_statuses = filters.validationStatuses;
    }
    if (filters.validationTargetTags.length) {
      f.validation_target_tags = filters.validationTargetTags;
    }
    if (filters.validationReasons.length) {
      f.validation_reasons = filters.validationReasons;
    }
    if (filters.scoreMin > 0) {
      f.score_min = filters.scoreMin;
    }
    if (filters.scoreMax < MATCH_SCALE_MAX) {
      f.score_max = filters.scoreMax;
    }
    if (filters.recordId) {
      f.record_ids = [filters.recordId];
    }
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
    setBoolFilter,
    clearFilters,
    buildRecordFilter,
    buildSearchPayload,
  };
}
