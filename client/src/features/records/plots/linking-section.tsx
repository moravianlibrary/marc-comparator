import { useTranslation } from 'react-i18next';
import { FacetPillRows, type PillGroup } from './facet-pills';

interface LinkingSectionProps {
  pillGroups: PillGroup[];
}

/**
 * What linking made of the catalogue.
 *
 * The section the dashboard was missing. Its facets used to sit in a
 * catch-all called "context" together with three that belonged to the
 * other sections — which is how the outcome of the tool's main job ended
 * up filed under no heading at all.
 *
 * Pill rows only for now; the charts that would go here (outcome over
 * time, confidence against outcome) do not exist yet.
 */
export function LinkingSection({ pillGroups }: LinkingSectionProps) {
  const { t } = useTranslation('records');

  return (
    <section className="space-y-2">
      <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
        {t('plots.sections.linking')}
      </h3>
      {/* Boxed: this section has no charts of its own, so the rows are its
          body and need a card to sit in. The other three put their rows
          above charts that are already cards. */}
      <FacetPillRows groups={pillGroups} boxed />
    </section>
  );
}
