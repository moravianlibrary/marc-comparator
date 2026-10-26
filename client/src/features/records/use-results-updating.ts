// Whether the records page is waiting on results for the filters it shows.
//
// The search and facets keep the previous filter's results on screen until the new ones arrive,
// which for a broad filter takes seconds. This says when that is happening, without subscribing
// to the queries themselves: a tab that does not show facets must not start fetching them.

import { type QueryKey, useIsFetching } from '@tanstack/react-query';

// Facet previews are left out on purpose: hovering a pill prefetches one, and that is not the
// page waiting on anything.
const RESULT_QUERIES = new Set(['search', 'facets']);

function isResultQuery(queryKey: QueryKey): boolean {
  return queryKey[0] === 'catalog-records' && RESULT_QUERIES.has(String(queryKey[1]));
}

export function useResultsUpdating(): boolean {
  return useIsFetching({ predicate: query => isResultQuery(query.queryKey) }) > 0;
}
