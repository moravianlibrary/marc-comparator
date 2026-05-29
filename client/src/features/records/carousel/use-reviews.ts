import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useTranslation } from "react-i18next";
import apiClient from "@/lib/api-client";
import type { RecordReviewsResponse } from "../types";

export function useRecordReviews(base: string, systemNumber: string) {
  return useQuery<RecordReviewsResponse>({
    queryKey: ["catalog-records", "reviews", base, systemNumber],
    queryFn: () =>
      apiClient
        .get<RecordReviewsResponse>(
          `/catalog-records/${base}/${systemNumber}/reviews`,
        )
        .then((r) => r.data),
  });
}

export function useCreateReview(base: string, systemNumber: string) {
  const queryClient = useQueryClient();
  const { t } = useTranslation("records");
  return useMutation({
    mutationFn: (data: { aspect_name: string; note?: string }) =>
      apiClient.post(`/catalog-records/${base}/${systemNumber}/review`, data),
    onSuccess: () => {
      toast.success(t("carousel.review.created"));
      queryClient.invalidateQueries({
        queryKey: ["catalog-records", "reviews", base, systemNumber],
      });
      queryClient.invalidateQueries({ queryKey: ["catalog-records", "search"] });
      queryClient.invalidateQueries({ queryKey: ["facets"] });
    },
  });
}

export function useDeleteReview(base: string, systemNumber: string) {
  const queryClient = useQueryClient();
  const { t } = useTranslation("records");
  return useMutation({
    mutationFn: (aspectName: string) =>
      apiClient.delete(
        `/catalog-records/${base}/${systemNumber}/review`,
        { params: { aspect_name: aspectName } },
      ),
    onSuccess: () => {
      toast.success(t("carousel.review.deleted"));
      queryClient.invalidateQueries({
        queryKey: ["catalog-records", "reviews", base, systemNumber],
      });
      queryClient.invalidateQueries({ queryKey: ["catalog-records", "search"] });
      queryClient.invalidateQueries({ queryKey: ["facets"] });
    },
  });
}
