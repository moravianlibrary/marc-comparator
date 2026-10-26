// The record detail's comparison section: one card per compared base, the chosen record first.
//
// Each row is one record compared with ours — the linked one with its stored comparison, the
// runner-ups and the records cataloguers ruled on with a comparison made on demand — together
// with how it was found and what a cataloguer said about it. Grouping comes from
// `../comparison-groups`.

import { Gavel, Link2Off, TriangleAlert, UserCheck, X } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Textarea } from '@/components/ui/textarea';
import { useHasPermission } from '@/hooks/use-permissions';
import { cn } from '@/lib/utils';
import { Permission } from '@/types/permission';
import { type ComparedRecord, type ComparisonGroup, comparisonGroups } from '../comparison-groups';
import type { DecisionRow } from '../link-decisions';
import { formatScore } from '../score';
import { LINK_OUTCOME_COLORS, type ClaimVerdict, type RecordSummary } from '../types';
import { useClaimLink, useWithdrawClaim } from './use-claims';
import { useRouteLabel } from './use-route-label';

function ClaimActions({ recordId, row }: { recordId: string; row: DecisionRow }) {
  const { t } = useTranslation('records');
  const claim = useClaimLink(recordId);
  const withdraw = useWithdrawClaim(recordId);
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState('');

  function decide(verdict: ClaimVerdict) {
    claim.mutate(
      {
        base: row.base,
        authority_base: row.authorityBase,
        authority_sysno: row.authoritySysno,
        verdict,
        note: note || undefined,
      },
      {
        onSuccess: () => {
          setOpen(false);
          setNote('');
        },
      },
    );
  }

  if (row.claim) {
    return (
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button variant="ghost" size="sm" className="h-6 px-2 text-xs gap-1">
            <X className="h-3 w-3" />
            {t('carousel.decisions.withdraw')}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-72">
          <div className="space-y-3">
            {row.claim.note && <p className="text-sm">{row.claim.note}</p>}
            <p className="text-xs text-muted-foreground">
              {new Date(row.claim.claimed_at).toLocaleString('cs-CZ')}
            </p>
            <p className="text-sm">{t('carousel.decisions.withdraw-explained')}</p>
            <div className="flex justify-end">
              <Button
                variant="ghost"
                size="sm"
                className="gap-1 text-destructive"
                disabled={withdraw.isPending}
                onClick={() =>
                  withdraw.mutate(
                    {
                      base: row.base,
                      authorityBase: row.authorityBase,
                      authoritySysno: row.authoritySysno,
                    },
                    { onSuccess: () => setOpen(false) },
                  )
                }
              >
                <Link2Off className="h-3.5 w-3.5" />
                {t('carousel.decisions.withdraw')}
              </Button>
            </div>
          </div>
        </PopoverContent>
      </Popover>
    );
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm" className="h-6 px-2 text-xs gap-1">
          <Gavel className="h-3 w-3" />
          {t('carousel.decisions.decide')}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80">
        <div className="space-y-3">
          <p className="text-sm font-medium">
            {row.authorityBase}-{row.authoritySysno}
          </p>
          <p className="text-xs text-muted-foreground">
            {t('carousel.decisions.decide-explained')}
          </p>
          <Textarea
            value={note}
            onChange={e => setNote(e.target.value)}
            placeholder={t('carousel.decisions.note-placeholder')}
            rows={2}
            className="text-sm"
          />
          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={claim.isPending}
              onClick={() => decide('NotSameWork')}
            >
              {t('carousel.decisions.not-same-work')}
            </Button>
            <Button size="sm" disabled={claim.isPending} onClick={() => decide('SameWork')}>
              {t('carousel.decisions.same-work')}
            </Button>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}

interface ComparedRecordRowProps {
  recordId: string;
  compared: ComparedRecord;
  isSelected: boolean;
  canReview: boolean;
  onSelectView?: (viewKey: string) => void;
}

function ComparedRecordRow({
  recordId,
  compared,
  isSelected,
  canReview,
  onSelectView,
}: ComparedRecordRowProps) {
  const { t } = useTranslation('records');
  const routeLabel = useRouteLabel();
  const row = compared.decision;
  const attempt = row?.attempt ?? null;
  const route = attempt ? routeLabel(attempt.matched_by, attempt.matched_identifier) : null;

  return (
    <div
      className={cn(
        'flex flex-wrap items-center gap-x-2 gap-y-1 border-t border-l-2 border-l-transparent px-2 py-1.5 text-xs first:border-t-0',
        compared.role === 'chosen' && 'border-l-primary bg-muted/40',
        isSelected && 'bg-accent',
      )}
    >
      <span
        className={cn(
          'w-20 shrink-0 text-muted-foreground',
          compared.role === 'chosen' && 'font-medium text-foreground',
        )}
      >
        {t(`carousel.comparison-role.${compared.role}`)}
      </span>

      {onSelectView ? (
        <button
          type="button"
          className="font-mono underline-offset-2 hover:underline"
          onClick={() => onSelectView(compared.viewKey)}
        >
          {compared.recordId}
        </button>
      ) : (
        <span className="font-mono">{compared.recordId}</span>
      )}

      {route && <span className="text-muted-foreground">{route}</span>}

      {attempt?.linker && (
        <span className="text-muted-foreground">
          {t(`linker-name.${attempt.linker}`, { defaultValue: attempt.linker })}
        </span>
      )}

      {row && !attempt && (
        <span className="text-muted-foreground italic">
          {t('carousel.decisions.not-in-this-pass')}
        </span>
      )}

      <span className="ml-auto flex flex-wrap items-center gap-2">
        {compared.score !== null && (
          <span className="font-medium">{formatScore(compared.score)}</span>
        )}

        {row?.claim && (
          <Badge
            variant="outline"
            className={cn(
              'text-[10px] gap-1',
              row.claim.verdict === 'SameWork' ? 'claim-same-work' : 'claim-not-same-work',
            )}
            title={row.claim.note ?? undefined}
          >
            <UserCheck className="h-3 w-3" />
            {t(`carousel.decisions.verdict.${row.claim.verdict}`)}
          </Badge>
        )}

        {row?.claim?.needs_review && (
          <Badge
            variant="outline"
            className="text-[10px] gap-1 claim-needs-review"
            title={t('carousel.decisions.needs-review-explained')}
          >
            <TriangleAlert className="h-3 w-3" />
            {t('carousel.decisions.needs-review')}
          </Badge>
        )}

        {canReview && row && <ClaimActions recordId={recordId} row={row} />}
      </span>
    </div>
  );
}

interface ComparisonGroupCardProps {
  recordId: string;
  group: ComparisonGroup;
  selectedView?: string;
  canReview: boolean;
  onSelectView?: (viewKey: string) => void;
}

function ComparisonGroupCard({
  recordId,
  group,
  selectedView,
  canReview,
  onSelectView,
}: ComparisonGroupCardProps) {
  const { t } = useTranslation('records');
  const answer = group.answer;

  return (
    <div className="overflow-hidden rounded-md border">
      <div className="flex flex-wrap items-center gap-2 border-b bg-muted/30 px-2 py-1.5 text-xs">
        <span className="font-medium">{group.base}</span>
        {answer && (
          <Badge
            variant="outline"
            className={cn('text-[10px]', LINK_OUTCOME_COLORS[answer.outcome])}
            title={answer.detail ?? undefined}
          >
            {t(`link-outcome-short.${answer.outcome}`)}
          </Badge>
        )}
        {answer?.candidate_count ? (
          <span className="text-muted-foreground">
            {t('carousel.weighed', { count: answer.candidate_count })}
          </span>
        ) : null}
      </div>

      {group.records.map(compared => (
        <ComparedRecordRow
          key={compared.recordId}
          recordId={recordId}
          compared={compared}
          isSelected={compared.viewKey === selectedView}
          canReview={canReview}
          onSelectView={onSelectView}
        />
      ))}
    </div>
  );
}

interface ComparisonGroupsProps {
  record: RecordSummary;
  selectedView?: string;
  onSelectView?: (viewKey: string) => void;
}

/**
 * Every base the record was compared against, and every record compared from it.
 *
 * Also the one place a link decision is visible whole — the answer, the runner-ups it was
 * chosen over, how each was found and the verdicts people entered against them — and where a
 * cataloguer enters one.
 */
export function ComparisonGroups({ record, selectedView, onSelectView }: ComparisonGroupsProps) {
  const { t } = useTranslation('records');
  const { hasPermission } = useHasPermission();
  const canReview = hasPermission(Permission.ReviewRecords) === true;
  const groups = comparisonGroups(record);

  if (groups.length === 0) {
    return null;
  }

  return (
    <div className="space-y-1">
      <p className="text-xs font-medium text-muted-foreground">{t('carousel.comparisons')}</p>
      <div className="space-y-2">
        {groups.map(group => (
          <ComparisonGroupCard
            key={group.base}
            recordId={record.id}
            group={group}
            selectedView={selectedView}
            canReview={canReview}
            onSelectView={onSelectView}
          />
        ))}
      </div>
    </div>
  );
}
