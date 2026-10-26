// How a compared record was found, in words, for the record detail's badges and rows.

import { useTranslation } from 'react-i18next';

/** How a pair was found, in words — or nothing where the row does not say. */
export function useRouteLabel() {
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
