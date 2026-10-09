import { Card, CardContent } from '@/components/ui/card';
import { ChevronDown, ChevronUp, Search, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import type { FacetBucket } from '../types';
import { PillList } from './pill-list';

export interface PillGroup {
  label: string;
  facetField: string;
  /** The pills to render: already searched and sliced by the caller. */
  buckets: FacetBucket[];
  /** How many values the facet has in total, before searching or slicing. */
  totalBuckets: number;
  /** Whether this group is long enough to be collapsed and searched at all. */
  collapsible: boolean;
  expanded: boolean;
  onToggleExpanded: () => void;
  search: string;
  onSearchChange: (value: string) => void;
  previewBuckets?: FacetBucket[];
  activeValues: string[];
  formatLabel?: (k: string) => string;
  onToggle: (value: string) => void;
  onHover: (value: string) => void;
  onLeave: () => void;
}

/**
 * A facet with exactly one value, rendered as one chip rather than a row.
 *
 * `Báze autorit` has only ever held SKC, `Báze porovnání` the same, and
 * `Validátory` only Kramerius. Each still selects a real subset — 8.6%,
 * 8.6% and 77.7% of the catalogue — so they are worth clicking, but a
 * heading and a row of its own for a single pill is four lines spent on
 * one fact. Several of them share one wrapped line instead.
 */
function SingleValueChip({ group }: { group: PillGroup }) {
  const bucket = group.buckets[0];
  if (!bucket) {
    // The search hid it. A one-value facet has nothing to search, so this is
    // only reachable if the caller slices before handing the group over.
    return null;
  }
  const isActive = group.activeValues.includes(bucket.key);
  const previewCount = group.previewBuckets?.find(p => p.key === bucket.key)?.count;
  const isDisabled = previewCount === 0 && !isActive;

  return (
    <button
      type="button"
      disabled={isDisabled}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-sm transition-colors',
        isDisabled
          ? 'bg-muted text-muted-foreground opacity-30 cursor-not-allowed'
          : isActive
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted text-foreground hover:bg-accent',
      )}
      onClick={() => group.onToggle(bucket.key)}
      onMouseEnter={() => group.onHover(bucket.key)}
      onMouseLeave={group.onLeave}
    >
      <span className={isActive ? 'opacity-80' : 'text-muted-foreground'}>{group.label}:</span>
      <span className="font-medium">
        {group.formatLabel ? group.formatLabel(bucket.key) : bucket.key}
      </span>
      <span
        className={cn(
          'text-xs tabular-nums rounded px-1 py-0.5',
          isActive
            ? 'bg-primary-foreground/20 text-primary-foreground/70'
            : 'bg-foreground text-background',
        )}
      >
        {bucket.count.toLocaleString('cs-CZ')}
      </span>
    </button>
  );
}

/**
 * A facet rendered as a labelled row of pills.
 *
 * A group only grows its search box and its "show more" when it is long
 * enough to need them. One facet here is: the cataloguing agency of the
 * linked record, 263 values of which 187 name ten records or fewer. Listed
 * in full it was longer than the rest of the dashboard put together.
 */
function PillRow({ group }: { group: PillGroup }) {
  const { t } = useTranslation('records');
  const hidden = group.totalBuckets - group.buckets.length;

  return (
    <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1.5">
      <div className="flex items-baseline gap-2 shrink-0">
        <p className="text-sm font-medium">{group.label}</p>
        {group.collapsible && (
          <span className="text-xs tabular-nums text-muted-foreground">{group.totalBuckets}</span>
        )}
      </div>

      {group.collapsible && group.expanded && (
        <div className="relative w-56 shrink-0">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            value={group.search}
            onChange={e => group.onSearchChange(e.target.value)}
            placeholder={t('plots.pill-group.search')}
            className="h-8 pl-7 pr-7 text-sm"
          />
          {group.search && (
            <button
              type="button"
              aria-label={t('plots.pill-group.clear-search')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              onClick={() => group.onSearchChange('')}
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      )}

      {group.buckets.length > 0 ? (
        // Expanded, the list is capped in height rather than in length: the
        // point of expanding is to reach a value, and a scroll box keeps the
        // sections below it where the eye left them.
        <div
          className={
            group.expanded
              ? 'max-h-56 w-full overflow-y-auto rounded-md border bg-muted/30 p-2'
              : undefined
          }
        >
          <PillList
            buckets={group.buckets}
            previewBuckets={group.previewBuckets}
            activeValues={group.activeValues}
            onToggle={group.onToggle}
            onHover={group.onHover}
            onLeave={group.onLeave}
            formatLabel={group.formatLabel}
          />
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">{t('plots.pill-group.no-match')}</p>
      )}

      {group.collapsible && (
        <button
          type="button"
          className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground whitespace-nowrap"
          onClick={group.onToggleExpanded}
        >
          {group.expanded ? (
            <>
              <ChevronUp className="h-3 w-3" />
              {t('plots.show-less')}
            </>
          ) : (
            <>
              <ChevronDown className="h-3 w-3" />
              {t('plots.pill-group.show-more', { count: hidden })}
            </>
          )}
        </button>
      )}
    </div>
  );
}

/**
 * The pill rows belonging to one section.
 *
 * Single-value facets are gathered onto a shared line at the bottom: they
 * are one fact each and reading them as a list is faster than reading them
 * as three stacked rows.
 *
 * `boxed` says these rows are the section's whole content rather than a
 * strip above its charts. Where there are charts, each is already a card and
 * a second card around two pills is a tall bordered box spent on one line —
 * which is what made `Báze` and the single-value sections look like a
 * heading had failed to render. Where there are no charts the rows are the
 * body, and without a card the section has nothing holding it at all.
 */
export function FacetPillRows({ groups, boxed = false }: { groups: PillGroup[]; boxed?: boolean }) {
  if (groups.length === 0) {
    return null;
  }

  const rows = groups.filter(g => g.totalBuckets > 1);
  const chips = groups.filter(g => g.totalBuckets === 1);
  // Clearly more than the 6px a row leaves between its own wrapped lines, so
  // a group that wraps still reads as one group rather than as two.
  const body = (
    <div className="space-y-4">
      {rows.map(group => (
        <PillRow key={group.facetField} group={group} />
      ))}
      {chips.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {chips.map(group => (
            <SingleValueChip key={group.facetField} group={group} />
          ))}
        </div>
      )}
    </div>
  );

  if (!boxed) {
    return body;
  }

  // `Card` brings its own py-6, so CardContent only needs the sides.
  return (
    <Card>
      <CardContent>{body}</CardContent>
    </Card>
  );
}
