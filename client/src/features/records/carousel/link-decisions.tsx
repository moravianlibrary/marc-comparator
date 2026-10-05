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
import { type BaseDecision, type DecisionRow, decisionsByBase, rowKey } from '../link-decisions';
import { formatScore } from '../score';
import { LINK_OUTCOME_COLORS, type ClaimVerdict, type RecordSummary } from '../types';
import { useClaimLink, useWithdrawClaim } from './use-claims';

/** How a pair was found, in words — or nothing where the row does not say. */
function useRouteLabel() {
  const { t } = useTranslation('records');
  return (matchedBy: string | null, matchedIdentifier: string | null): string | null => {
    if (!matchedBy) {
      return null;
    }
    // An identifier route is only readable once it says *which* identifier:
    // a shared ČNB number and a shared ISBN are both "found by identifier"
    // and a low score means opposite things for the two.
    if (matchedBy === 'identifier' && matchedIdentifier) {
      return t('carousel.decisions.matched-by', {
        route: t(`match-identifier.${matchedIdentifier}`, { defaultValue: matchedIdentifier }),
      });
    }
    return t('carousel.decisions.matched-by', {
      route: t(`match-route.${matchedBy}`, { defaultValue: matchedBy }),
    });
  };
}

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

function DecisionRowView({
  recordId,
  row,
  canReview,
  onSelectView,
}: {
  recordId: string;
  row: DecisionRow;
  canReview: boolean;
  onSelectView?: (viewKey: string) => void;
}) {
  const { t } = useTranslation('records');
  const routeLabel = useRouteLabel();
  const attempt = row.attempt;
  const score = attempt && attempt.confidence !== null ? formatScore(attempt.confidence) : null;
  const route = attempt ? routeLabel(attempt.matched_by, attempt.matched_identifier) : null;

  // Only an accepted link has a catalogue record of its own, and only that
  // one can be opened beside ours. A candidate nobody accepted has its MARC
  // in storage but no row to address, so there is nothing to navigate to.
  const viewKey = attempt?.authority_record_id
    ? `auth:${row.base}:${row.authoritySysno}`
    : undefined;

  return (
    <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
      {viewKey && onSelectView ? (
        <button
          type="button"
          className="font-mono underline-offset-2 hover:underline"
          onClick={() => onSelectView(viewKey)}
        >
          {row.authorityBase}-{row.authoritySysno}
        </button>
      ) : (
        <span className="font-mono">
          {row.authorityBase}-{row.authoritySysno}
        </span>
      )}

      <Badge variant="outline" className="text-[10px] font-normal">
        {row.isAnswer ? t('carousel.decisions.answer') : t('carousel.decisions.alternative')}
      </Badge>

      {score && <span className="text-muted-foreground">{score}</span>}

      {route && <span className="text-muted-foreground">{route}</span>}

      {attempt?.linker && (
        <span className="text-muted-foreground">
          {t(`linker-name.${attempt.linker}`, { defaultValue: attempt.linker })}
        </span>
      )}

      {!attempt && (
        <span className="text-muted-foreground italic">
          {t('carousel.decisions.not-in-this-pass')}
        </span>
      )}

      {row.claim && (
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

      {row.claim?.needs_review && (
        <Badge
          variant="outline"
          className="text-[10px] gap-1 claim-needs-review"
          title={t('carousel.decisions.needs-review-explained')}
        >
          <TriangleAlert className="h-3 w-3" />
          {t('carousel.decisions.needs-review')}
        </Badge>
      )}

      {canReview && <ClaimActions recordId={recordId} row={row} />}
    </div>
  );
}

function BaseDecisionView({
  recordId,
  decision,
  canReview,
  onSelectView,
}: {
  recordId: string;
  decision: BaseDecision;
  canReview: boolean;
  onSelectView?: (viewKey: string) => void;
}) {
  const { t } = useTranslation('records');
  const answer = decision.answer;

  return (
    <div className="rounded-md border px-2 py-1.5 space-y-1">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="font-medium">{decision.base}</span>
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

      {decision.rows.map(row => (
        <DecisionRowView
          key={rowKey(row)}
          recordId={recordId}
          row={row}
          canReview={canReview}
          onSelectView={onSelectView}
        />
      ))}
    </div>
  );
}

/**
 * What linking concluded for each base, and what a cataloguer made of it.
 *
 * This is the one place the whole of a link decision is visible: the answer,
 * the runner-ups it was chosen over, how each was found, and the verdicts
 * people have entered against them. Everything here was already arriving on
 * the record summary and was rendered nowhere, which left the claim feature
 * reachable only through the API.
 */
export function LinkDecisions({
  record,
  onSelectView,
}: {
  record: RecordSummary;
  onSelectView?: (viewKey: string) => void;
}) {
  const { t } = useTranslation('records');
  const { hasPermission } = useHasPermission();
  const canReview = hasPermission(Permission.ReviewRecords) === true;

  const decisions = decisionsByBase(record).filter(d => d.rows.length > 0);
  if (decisions.length === 0) {
    return null;
  }

  return (
    <div className="space-y-1">
      <p className="text-xs font-medium text-muted-foreground">{t('carousel.decisions.title')}</p>
      <div className="space-y-1">
        {decisions.map(decision => (
          <BaseDecisionView
            key={decision.base}
            recordId={record.id}
            decision={decision}
            canReview={canReview}
            onSelectView={onSelectView}
          />
        ))}
      </div>
    </div>
  );
}
