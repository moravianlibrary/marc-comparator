import { useQuery } from '@tanstack/react-query';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { SkeletonMarcTable } from '@/components/skeletons/skeleton-marc-table';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import apiClient from '@/lib/api-client';
import type { SystemInfo } from '@/types/settings';
import { type ComparisonGroup, comparisonGroups } from '../comparison-groups';
import { hasCandidate } from '../link-decisions';
import { formatScore, formatScoreShort } from '../score';
import type {
  ComparisonDetail,
  ComparisonResult,
  FieldComparisonResult,
  MarcRecordData,
  RecordSummary,
  SearchRecordsResponse,
  ValidationDetail,
  ValidationResult,
} from '../types';
import { useRecordFilters } from '../use-record-filters';
import type { AnnotationType } from './marc-table';
import { MarcTable } from './marc-table';
import { RecordHeader } from './record-header';
import { ReviewButton } from './review-button';
import { useRecordReviews } from './use-reviews';

type ViewOption =
  | { kind: 'marc' }
  // A record compared with ours that has no stored comparison: the runner-ups, and a linked
  // record compared before comparisons were stored. Read from the MARC kept when it was
  // proposed, compared on demand, and possibly missing entirely.
  | { kind: 'candidate'; base: string; systemNumber: string }
  | { kind: 'comparison'; comparator: string; otherRecordId: string }
  | { kind: 'validation'; validatorName: string };

function parseViewKey(key: string): ViewOption {
  if (key.startsWith('cand:')) {
    const rest = key.slice(5);
    const sepIdx = rest.indexOf(':');
    return { kind: 'candidate', base: rest.slice(0, sepIdx), systemNumber: rest.slice(sepIdx + 1) };
  }
  if (key.startsWith('comp:')) {
    const rest = key.slice(5);
    const sepIdx = rest.indexOf(':');
    return {
      kind: 'comparison',
      comparator: rest.slice(0, sepIdx),
      otherRecordId: rest.slice(sepIdx + 1),
    };
  }
  if (key.startsWith('val:')) {
    return { kind: 'validation', validatorName: key.slice(4) };
  }
  return { kind: 'marc' };
}

/**
 * The base a view compares against, read from its key alone so it survives a record switch.
 *
 * A compared record's id is `<base>-<system number>`, and a candidate key names its base.
 */
function comparedBaseOfView(view: ViewOption): string | null {
  if (view.kind === 'candidate') {
    return view.base;
  }

  if (view.kind === 'comparison') {
    return view.otherRecordId.split('-')[0] ?? null;
  }

  return null;
}

/**
 * Whether the record has what the view shows, judged from the record's own summary.
 *
 * The summary arrives with the search, so a record switch can answer this at once, without
 * waiting for the detail queries.
 */
function isViewAvailable(key: string, record: RecordSummary): boolean {
  const opt = parseViewKey(key);
  switch (opt.kind) {
    case 'marc':
      return true;
    case 'candidate':
      return hasCandidate(record, opt.base, opt.systemNumber);
    case 'comparison':
      return record.comparisons.some(
        c => c.comparator === opt.comparator && c.other_record_id === opt.otherRecordId,
      );
    case 'validation':
      return record.validations.some(v => v.validator === opt.validatorName);
  }
}

/**
 * The view to show for this record: the selected one where the record has it, else the same
 * compared base's chosen record, else its MARC.
 *
 * Derived on every render rather than written back to the URL when the record changes. That
 * second write, made right after the one moving to the next record, could be built from the URL
 * before the move and put the previous record back for a moment.
 */
function resolveView(selectedView: string, record: RecordSummary): string {
  if (isViewAvailable(selectedView, record)) {
    return selectedView;
  }

  const base = comparedBaseOfView(parseViewKey(selectedView));
  const sameBase = comparisonGroups(record).find(g => g.base === base);
  return sameBase?.records[0]?.viewKey ?? 'marc';
}

function RecordDetail({
  record,
  selectedView,
  setSelectedView,
  targetFieldsOnly,
  setTargetFieldsOnly,
}: {
  record: RecordSummary;
  selectedView: string;
  setSelectedView: (v: string) => void;
  targetFieldsOnly: boolean;
  setTargetFieldsOnly: (v: boolean) => void;
}) {
  const { t } = useTranslation('records');

  const base = record.base;
  const systemNumber = record.system_number;

  const { data: marcData, isLoading: marcLoading } = useQuery<MarcRecordData>({
    queryKey: ['catalog-records', 'marc', base, systemNumber],
    queryFn: () =>
      apiClient
        .get<MarcRecordData>(`/catalog-records/${base}/${systemNumber}/marc`)
        .then(r => r.data),
  });

  const { data: comparisons, isFetching: comparisonsFetching } = useQuery<ComparisonDetail[]>({
    queryKey: ['catalog-records', 'comparisons', base, systemNumber],
    queryFn: () =>
      apiClient
        .get<ComparisonDetail[]>(`/catalog-records/${base}/${systemNumber}/comparisons`)
        .then(r => r.data),
  });

  const { data: validations, isFetching: validationsFetching } = useQuery<ValidationDetail[]>({
    queryKey: ['catalog-records', 'validations', base, systemNumber],
    queryFn: () =>
      apiClient
        .get<ValidationDetail[]>(`/catalog-records/${base}/${systemNumber}/validations`)
        .then(r => r.data),
  });

  const { data: reviews } = useRecordReviews(base, systemNumber);

  const { data: systemInfo } = useQuery<SystemInfo>({
    queryKey: ['system', 'info'],
    queryFn: () => apiClient.get<SystemInfo>('/system/info').then(r => r.data),
  });
  const krameriusClientUrl = systemInfo?.kramerius_client_urls?.[record.base] ?? undefined;

  const view = resolveView(selectedView, record);
  const viewOpt = parseViewKey(view);

  const candidateBase = viewOpt.kind === 'candidate' ? viewOpt.base : '';
  const candidateSysno = viewOpt.kind === 'candidate' ? viewOpt.systemNumber : '';
  const {
    data: candidateMarcData,
    isLoading: candidateMarcLoading,
    isError: candidateMarcMissing,
  } = useQuery<MarcRecordData>({
    queryKey: ['catalog-records', 'candidate-marc', candidateBase, candidateSysno],
    queryFn: () =>
      apiClient
        .get<MarcRecordData>(
          `/authority-linking/candidates/${candidateBase}/${candidateSysno}/marc`,
          // We keep no copy of some candidates — a linker that assembles one
          // has no bytes to keep — so a 404 here is an answer, not an
          // incident, and it says so in place of the table.
          { suppressErrorToast: true },
        )
        .then(r => r.data),
    enabled: !!candidateBase && !!candidateSysno,
    retry: false,
  });

  const {
    data: candidateComparison,
    isLoading: candidateComparisonLoading,
    isError: candidateComparisonError,
  } = useQuery<ComparisonResult>({
    queryKey: [
      'catalog-records',
      'candidate-comparison',
      base,
      systemNumber,
      candidateBase,
      candidateSysno,
    ],
    queryFn: () =>
      apiClient
        .get<ComparisonResult>(
          `/authority-linking/candidates/${candidateBase}/${candidateSysno}/comparison`,
          {
            params: { main_base: base, main_sysno: systemNumber },
            suppressErrorToast: true,
          },
        )
        .then(r => r.data),
    enabled: !!candidateMarcData && !!candidateBase && !!candidateSysno,
    retry: false,
  });

  const groups = comparisonGroups(record);

  const validatorNames = [...new Set((validations ?? []).map(v => v.validator))];
  const validationOptions = validatorNames.map(name => ({
    key: `val:${name}`,
    label: t(`validator-name.${name}`, { defaultValue: name }),
  }));

  let annotationType: AnnotationType | undefined;
  let comparisonAnnotations: FieldComparisonResult[] | undefined;
  let validationAnnotations: ValidationResult[] | undefined;

  const matchedComparison =
    viewOpt.kind === 'comparison' && comparisons
      ? comparisons.find(
          c => c.comparator === viewOpt.comparator && c.other_record_id === viewOpt.otherRecordId,
        )
      : undefined;
  if (matchedComparison) {
    annotationType = 'comparison';
    comparisonAnnotations = matchedComparison.result.field_results ?? undefined;
  } else if (viewOpt.kind === 'candidate' && candidateComparison) {
    annotationType = 'comparison';
    comparisonAnnotations = candidateComparison.field_results ?? undefined;
  } else if (viewOpt.kind === 'validation' && validations) {
    annotationType = 'validation';
    validationAnnotations = validations
      .filter(v => v.validator === viewOpt.validatorName)
      .map(v => v.result);
  }

  const isCandidate = viewOpt.kind === 'candidate';
  const displayMarc = isCandidate && !candidateComparison ? candidateMarcData : marcData;
  const annotationLoading =
    (viewOpt.kind === 'comparison' && comparisonsFetching) ||
    (viewOpt.kind === 'validation' && validationsFetching) ||
    (isCandidate && candidateMarcLoading) ||
    (isCandidate && !!candidateMarcData && candidateComparisonLoading);
  const ownMarcLoading = isCandidate ? candidateMarcLoading : marcLoading;
  const displayLoading =
    ownMarcLoading || annotationLoading || (isCandidate && !!candidateComparison && marcLoading);

  const hasAnnotation = annotationType !== undefined;
  const targetTags = new Set<string>();
  if (targetFieldsOnly && hasAnnotation) {
    comparisonAnnotations?.forEach(a => {
      targetTags.add(a.tag);
    });
    validationAnnotations?.forEach(a => {
      targetTags.add(a.target.tag);
    });
  }

  return (
    <div className="space-y-4">
      <RecordHeader record={record} selectedView={view} onSelectView={setSelectedView} />

      <div className="flex flex-wrap items-center gap-4">
        <Select value={view} onValueChange={setSelectedView}>
          <SelectTrigger className="w-full sm:w-[320px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="marc">{t('carousel.marc-record')}</SelectItem>

            {groups.map(group => (
              <ComparisonOptions key={group.base} group={group} />
            ))}

            {validationOptions.length > 0 && (
              <>
                <SelectSeparator />
                <SelectGroup>
                  <SelectLabel>{t('carousel.validations')}</SelectLabel>
                  {validationOptions.map(opt => (
                    <SelectItem key={opt.key} value={opt.key}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectGroup>
              </>
            )}
          </SelectContent>
        </Select>

        {hasAnnotation && (
          <div className="flex items-center gap-2">
            <Checkbox
              id="target-fields-only"
              checked={targetFieldsOnly}
              onCheckedChange={checked => setTargetFieldsOnly(checked === true)}
            />
            <Label htmlFor="target-fields-only" className="text-sm cursor-pointer">
              {t('carousel.target-fields-only')}
            </Label>
          </div>
        )}

        {viewOpt.kind === 'comparison' && (
          <ReviewButton
            base={base}
            systemNumber={systemNumber}
            aspectName={viewOpt.comparator}
            currentReview={reviews?.current.find(r => r.aspect_name === viewOpt.comparator)}
            history={reviews?.history.filter(r => r.aspect_name === viewOpt.comparator) ?? []}
            reviewNotNeeded={
              comparisons?.find(
                c =>
                  c.comparator === viewOpt.comparator &&
                  c.other_record_id === viewOpt.otherRecordId,
              )?.result.match_quality === 'Excellent'
            }
          />
        )}
        {viewOpt.kind === 'validation' && (
          <ReviewButton
            base={base}
            systemNumber={systemNumber}
            aspectName={viewOpt.validatorName}
            currentReview={reviews?.current.find(r => r.aspect_name === viewOpt.validatorName)}
            history={reviews?.history.filter(r => r.aspect_name === viewOpt.validatorName) ?? []}
            reviewNotNeeded={validations
              ?.filter(v => v.validator === viewOpt.validatorName)
              .every(v => v.result.status === 'Valid' || v.result.status === 'AdditionalInfo')}
          />
        )}
      </div>

      {isCandidate && candidateComparison && (
        <p className="text-sm text-muted-foreground">
          {t('carousel.decisions.on-demand-score', {
            score: formatScore(candidateComparison.overall_score),
          })}
        </p>
      )}
      {isCandidate && candidateComparisonError && !candidateMarcMissing && (
        <p className="text-sm text-muted-foreground">
          {t('carousel.decisions.comparison-unavailable')}
        </p>
      )}

      {displayLoading ? (
        <SkeletonMarcTable showAnnotationColumn={viewOpt.kind !== 'marc'} />
      ) : displayMarc ? (
        <div className="animate-fade-in">
          <MarcTable
            marc={displayMarc}
            annotationType={annotationType}
            comparisonAnnotations={comparisonAnnotations}
            validationAnnotations={validationAnnotations}
            targetTags={targetFieldsOnly && targetTags.size > 0 ? targetTags : undefined}
            krameriusClientUrl={krameriusClientUrl}
          />
        </div>
      ) : isCandidate && candidateMarcMissing ? (
        <p className="text-muted-foreground">{t('carousel.decisions.no-stored-marc')}</p>
      ) : (
        <p className="text-muted-foreground">-</p>
      )}
    </div>
  );
}

/** One compared base in the view picker: its records, the chosen one first. */
function ComparisonOptions({ group }: { group: ComparisonGroup }) {
  const { t } = useTranslation('records');

  if (group.records.length === 0) {
    return null;
  }

  return (
    <>
      <SelectSeparator />
      <SelectGroup>
        <SelectLabel>
          {t('carousel.comparisons')} · {group.base}
        </SelectLabel>
        {group.records.map(compared => (
          <SelectItem key={compared.viewKey} value={compared.viewKey}>
            {[
              compared.recordId,
              compared.role === 'alternative'
                ? null
                : t(`carousel.comparison-role.${compared.role}`),
              compared.score === null ? null : formatScoreShort(compared.score),
            ]
              .filter(Boolean)
              .join(' · ')}
          </SelectItem>
        ))}
      </SelectGroup>
    </>
  );
}

export function CarouselView() {
  const { t } = useTranslation('records');
  const { filters, setFilters, buildSearchPayload } = useRecordFilters();
  const selectedView = filters.carouselView || 'marc';
  const setSelectedView = useCallback(
    (v: string) => setFilters({ carouselView: v === 'marc' ? '' : v }),
    [setFilters],
  );
  const [targetFieldsOnly, _setTargetFieldsOnly] = useState(
    () => localStorage.getItem('carousel:targetFieldsOnly') === 'true',
  );
  const setTargetFieldsOnly = useCallback((v: boolean) => {
    _setTargetFieldsOnly(v);
    localStorage.setItem('carousel:targetFieldsOnly', String(v));
  }, []);
  const prevRef = useRef<HTMLButtonElement>(null);
  const nextRef = useRef<HTMLButtonElement>(null);

  const payload = buildSearchPayload();
  const { data: searchData } = useQuery<SearchRecordsResponse>({
    queryKey: ['catalog-records', 'search', payload],
    queryFn: () =>
      apiClient.post<SearchRecordsResponse>('/catalog-records/search', payload).then(r => r.data),
  });

  const records = searchData?.items ?? [];
  const total = searchData?.total ?? 0;
  const recordIndex = Math.min(filters.recordIndex, Math.max(0, records.length - 1));
  const currentRecord = records.length > 0 ? records[recordIndex] : null;

  // Clamp recordIndex when data loads (e.g. last page has fewer items)
  useEffect(() => {
    if (records.length > 0 && filters.recordIndex >= records.length) {
      setFilters({ recordIndex: records.length - 1 });
    }
  }, [records.length, filters.recordIndex, setFilters]);

  // Cross-page navigation helpers
  const canGoPrev = recordIndex > 0 || filters.page > 1;
  const canGoNext = recordIndex < records.length - 1 || filters.page * filters.pageSize < total;

  const goToPrev = useCallback(() => {
    if (recordIndex > 0) {
      setFilters({ recordIndex: recordIndex - 1 });
      return;
    }

    if (filters.page > 1) {
      setFilters({ page: filters.page - 1, recordIndex: filters.pageSize - 1 });
    }
  }, [recordIndex, filters.page, filters.pageSize, setFilters]);

  const goToNext = useCallback(() => {
    if (recordIndex < records.length - 1) {
      setFilters({ recordIndex: recordIndex + 1 });
      return;
    }

    if (filters.page * filters.pageSize < total) {
      setFilters({ page: filters.page + 1, recordIndex: 0 });
    }
  }, [recordIndex, records.length, filters.page, filters.pageSize, total, setFilters]);

  // Keyboard navigation
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }
      if (e.key === 'a' && canGoPrev) {
        e.preventDefault();
        goToPrev();
      } else if (e.key === 'd' && canGoNext) {
        e.preventDefault();
        goToNext();
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [canGoPrev, canGoNext, goToPrev, goToNext]);

  if (records.length === 0) {
    return <p className="py-8 text-center text-muted-foreground">{t('carousel.no-record')}</p>;
  }

  // Single record — no carousel chrome
  if (records.length === 1 && total <= 1) {
    return (
      <div className="mx-2 sm:mx-12">
        <RecordDetail
          record={records[0]!}
          selectedView={selectedView}
          setSelectedView={setSelectedView}
          targetFieldsOnly={targetFieldsOnly}
          setTargetFieldsOnly={setTargetFieldsOnly}
        />
      </div>
    );
  }

  // Multiple records — use carousel
  return (
    <div className="relative">
      <div className="mx-2 sm:mx-12">
        <RecordDetail
          record={currentRecord!}
          selectedView={selectedView}
          setSelectedView={setSelectedView}
          targetFieldsOnly={targetFieldsOnly}
          setTargetFieldsOnly={setTargetFieldsOnly}
        />
      </div>
      <button
        type="button"
        ref={prevRef}
        onClick={goToPrev}
        disabled={!canGoPrev}
        className="fixed left-2 top-1/2 -translate-y-1/2 z-10 inline-flex h-8 w-8 items-center justify-center rounded-full border bg-background shadow-sm hover:bg-accent disabled:opacity-50 disabled:pointer-events-none"
        aria-label={t('carousel.previous')}
      >
        <ChevronLeft className="h-4 w-4" />
      </button>
      <button
        type="button"
        ref={nextRef}
        onClick={goToNext}
        disabled={!canGoNext}
        className="fixed right-2 top-1/2 -translate-y-1/2 z-10 inline-flex h-8 w-8 items-center justify-center rounded-full border bg-background shadow-sm hover:bg-accent disabled:opacity-50 disabled:pointer-events-none"
        aria-label={t('carousel.next')}
      >
        <ChevronRight className="h-4 w-4" />
      </button>
    </div>
  );
}
