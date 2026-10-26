import { Link2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useHasPermission } from '@/hooks/use-permissions';
import { cn } from '@/lib/utils';
import { Permission } from '@/types/permission';
import { type ComparisonGroup, comparisonGroups } from '../comparison-groups';
import { formatScore } from '../score';
import { AdvancedTaskActions, RecordTaskActions } from '../record-task-actions';
import { LINK_OUTCOME_COLORS, type RecordSummary, STATE_COLORS } from '../types';
import { COMPARISON_BADGE_CLASS, groupValidations, VALIDATION_BADGE_CLASS } from '../utils';
import { ComparisonGroups } from './comparison-groups';
import { useRouteLabel } from './use-route-label';

interface RecordHeaderProps {
  record: RecordSummary;
  selectedView?: string;
  onSelectView?: (viewKey: string) => void;
}

export function RecordHeader({ record, selectedView, onSelectView }: RecordHeaderProps) {
  const { t } = useTranslation('records');
  const { hasPermission } = useHasPermission();
  const canProcess = hasPermission(Permission.ProcessRecords) === true;
  const canRunPartial = hasPermission(Permission.RunPartialRecordTasks) === true;
  const filters = { record_ids: [record.id] };

  return (
    <div className="space-y-2 border-b pb-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">
          {record.base}-{record.system_number}
        </h2>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => {
              const url = new URL(window.location.origin + window.location.pathname);
              url.searchParams.set('tab', 'carousel');
              url.searchParams.set('recordId', record.id);
              navigator.clipboard.writeText(url.toString());
              toast.success(t('carousel.link-copied'));
            }}
            title={t('carousel.permalink')}
          >
            <Link2 className="h-4 w-4" />
          </Button>
          {canProcess && <RecordTaskActions filters={filters} totalCount={1} />}
          {canRunPartial && <AdvancedTaskActions filters={filters} totalCount={1} />}
        </div>
      </div>

      {record.title && <p className="text-base">{record.title}</p>}

      {record.authors.length > 0 && (
        <p className="text-sm text-muted-foreground">{record.authors.join(', ')}</p>
      )}

      {record.processing_error && (
        <p className="rounded-md border border-[var(--status-danger)] bg-[color-mix(in_oklch,var(--status-danger)_8%,transparent)] px-2 py-1 text-xs text-[var(--status-danger)]">
          {t('carousel.processing-error')}: <code>{record.processing_error}</code>
        </p>
      )}

      <div className="flex flex-wrap gap-1">
        {record.type_of_record && (
          <Badge variant="outline" className="text-xs">
            {t(`type-of-record.${record.type_of_record}`, { defaultValue: record.type_of_record })}
          </Badge>
        )}
        {record.bibliographic_level && (
          <Badge variant="outline" className="text-xs">
            {t(`bibliographic-level.${record.bibliographic_level}`, {
              defaultValue: record.bibliographic_level,
            })}
          </Badge>
        )}
        {record.state.map(s => (
          <Badge key={s} variant="outline" className={cn('text-xs', STATE_COLORS[s])}>
            {t(`state.${s}`)}
          </Badge>
        ))}
      </div>

      <div className="flex flex-wrap gap-2 text-xs">
        {comparisonGroups(record).map(group => (
          <ComparisonBadge key={group.base} group={group} onSelectView={onSelectView} />
        ))}
        {groupValidations(record.validations).map(g => {
          const viewKey = `val:${g.validator}`;
          return (
            <Badge
              key={`${g.validator}-${g.target_tag}-${g.status}`}
              variant="outline"
              className={cn(
                'text-xs',
                VALIDATION_BADGE_CLASS[g.status],
                onSelectView && 'cursor-pointer hover:bg-accent',
              )}
              onClick={onSelectView ? () => onSelectView(viewKey) : undefined}
            >
              {t(`validator-name.${g.validator}`)} [{g.target_tag}]:{' '}
              {t(`validity-status.${g.status}`)}
              {g.count > 1 && (
                <span className="ml-1 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-muted-foreground/20 px-1 text-[10px] font-medium">
                  {g.count}
                </span>
              )}
            </Badge>
          );
        })}
      </div>

      <ComparisonGroups record={record} selectedView={selectedView} onSelectView={onSelectView} />

      <div className="flex gap-4 text-xs text-muted-foreground">
        {record.latest_sync && (
          <span>
            {t('table.columns.latest-sync')}: {new Date(record.latest_sync).toLocaleString('cs-CZ')}
          </span>
        )}
      </div>
    </div>
  );
}

interface ComparisonBadgeProps {
  group: ComparisonGroup;
  onSelectView?: (viewKey: string) => void;
}

/**
 * One base in one badge: what linking concluded and how well the chosen record compares.
 *
 * The link and its comparison used to be two badges naming the same base and the same record.
 * The colour is the comparison's quality where there is one, else the link outcome's.
 */
function ComparisonBadge({ group, onSelectView }: ComparisonBadgeProps) {
  const { t } = useTranslation('records');
  const routeLabel = useRouteLabel();
  const answer = group.answer;
  const headline = group.records.find(r => r.role !== 'alternative') ?? null;
  const route = answer ? routeLabel(answer.matched_by, answer.matched_identifier) : null;
  const outcome = answer
    ? [t(`link-outcome-inline.${answer.outcome}`), route].filter(Boolean).join(' ')
    : null;
  const score = headline?.score != null ? formatScore(headline.score) : null;
  const colorClass = headline?.comparison
    ? COMPARISON_BADGE_CLASS[headline.comparison.match_quality]
    : answer && LINK_OUTCOME_COLORS[answer.outcome];
  const viewKey = headline?.viewKey;
  const isClickable = !!viewKey && !!onSelectView;

  return (
    <Badge
      variant="outline"
      className={cn('text-xs', colorClass, isClickable && 'cursor-pointer hover:bg-accent')}
      title={answer?.detail ?? undefined}
      onClick={isClickable ? () => onSelectView(viewKey) : undefined}
    >
      {[group.base, outcome, score].filter(Boolean).join(' · ')}
    </Badge>
  );
}
