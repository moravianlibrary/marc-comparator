import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import apiClient from '@/lib/api-client';
import type { LinkClaimRequest } from '../types';

/**
 * Why nothing here reads the claims back.
 *
 * A record's claims arrive on its summary, so the search query already holds
 * them and invalidating it is enough. The dedicated GET exists for callers
 * that hold a record id and nothing else; this screen is not one.
 *
 * The rows a claim moves are another matter: writing them means running the
 * linking pipeline, which the API does not do, so the server asks for a
 * scoped linking task instead. That is why both toasts say the link will
 * catch up — the verdict is stored at once, the answer is recomputed when
 * the task runs, and `useWsEvents` invalidates `catalog-records` when it
 * finishes.
 */
export function useClaimLink(recordId: string) {
  const queryClient = useQueryClient();
  const { t } = useTranslation('records');
  return useMutation({
    mutationFn: (data: LinkClaimRequest) =>
      apiClient.post(`/authority-linking/records/${recordId}/claims`, data),
    onSuccess: () => {
      toast.success(t('carousel.decisions.claimed'));
      queryClient.invalidateQueries({ queryKey: ['catalog-records', 'search'] });
      queryClient.invalidateQueries({ queryKey: ['facets'] });
    },
  });
}

export function useWithdrawClaim(recordId: string) {
  const queryClient = useQueryClient();
  const { t } = useTranslation('records');
  return useMutation({
    mutationFn: (pair: { base: string; authorityBase: string; authoritySysno: string }) =>
      apiClient.delete(
        `/authority-linking/records/${recordId}/claims/` +
          [pair.base, pair.authorityBase, pair.authoritySysno].map(encodeURIComponent).join('/'),
      ),
    onSuccess: () => {
      toast.success(t('carousel.decisions.withdrawn'));
      queryClient.invalidateQueries({ queryKey: ['catalog-records', 'search'] });
      queryClient.invalidateQueries({ queryKey: ['facets'] });
    },
  });
}
