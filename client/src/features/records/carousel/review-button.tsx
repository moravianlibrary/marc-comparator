import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Check, Clock, History, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Textarea } from "@/components/ui/textarea";
import { useHasPermission } from "@/hooks/use-permissions";
import { Permission } from "@/types/permission";
import type { ReviewDetail } from "../types";
import { useCreateReview, useDeleteReview } from "./use-reviews";

interface ReviewButtonProps {
  base: string;
  systemNumber: string;
  aspectName: string;
  currentReview: ReviewDetail | undefined;
  history: ReviewDetail[];
  reviewNotNeeded?: boolean;
}

export function ReviewButton({
  base,
  systemNumber,
  aspectName,
  currentReview,
  history,
  reviewNotNeeded,
}: ReviewButtonProps) {
  const { t } = useTranslation("records");
  const { hasPermission } = useHasPermission();
  const canReview = hasPermission(Permission.ReviewRecords);

  const createReview = useCreateReview(base, systemNumber);
  const deleteReview = useDeleteReview(base, systemNumber);

  const [open, setOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);

  const [note, setNote] = useState("");

  if (!canReview) return null;

  const allReviews = currentReview ? [currentReview, ...history] : history;
  const hasHistory = allReviews.length > 0;

  function handleSubmit() {
    createReview.mutate(
      { aspect_name: aspectName, note: note || undefined },
      { onSuccess: () => { setOpen(false); setNote(""); } },
    );
  }

  function handleRemove() {
    deleteReview.mutate(aspectName, {
      onSuccess: () => setOpen(false),
    });
  }

  const historyButton = hasHistory ? (
    <Popover open={historyOpen} onOpenChange={setHistoryOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="h-7 px-1.5 rounded-l-none border-l-0"
        >
          <History className="h-3.5 w-3.5" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80">
        <div className="space-y-3">
          <p className="text-sm font-medium">{t("carousel.review.history")}</p>
          <div className="max-h-60 overflow-y-auto space-y-2">
            {allReviews.map((r) => (
              <div key={r.id} className="border-b pb-2 last:border-b-0 last:pb-0">
                <div className="flex items-center gap-2 text-xs">
                  <span className="font-medium">
                    {r.reviewer_name ?? r.reviewed_by}
                  </span>
                  <span className="text-muted-foreground">
                    {new Date(r.reviewed_at).toLocaleString("cs")}
                  </span>
                </div>
                {r.note && (
                  <p className="text-xs text-muted-foreground mt-0.5">{r.note}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      </PopoverContent>
    </Popover>
  ) : null;

  if (reviewNotNeeded && !currentReview) {
    return (
      <div className="flex">
        <Button
          variant="outline"
          size="sm"
          className={cn("h-7 gap-1.5 text-xs", hasHistory && "rounded-r-none")}
          disabled
        >
          <Check className="h-3.5 w-3.5" />
          {t("carousel.review.not-needed")}
        </Button>
        {historyButton}
      </div>
    );
  }

  if (!currentReview) {
    return (
      <div className="flex">
        <Popover open={open} onOpenChange={setOpen}>
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className={cn("h-7 gap-1.5 text-xs", hasHistory && "rounded-r-none")}
            >
              <Check className="h-3.5 w-3.5" />
              {t("carousel.review.mark-reviewed")}
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-72">
            <div className="space-y-3">
              <p className="text-sm font-medium">{t("carousel.review.add-note")}</p>
              <Textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder={t("carousel.review.note-placeholder")}
                rows={3}
                className="text-sm"
              />
              <div className="flex justify-end gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setOpen(false)}
                >
                  {t("common:cancel")}
                </Button>
                <Button
                  size="sm"
                  onClick={handleSubmit}
                  disabled={createReview.isPending}
                >
                  {t("carousel.review.confirm")}
                </Button>
              </div>
            </div>
          </PopoverContent>
        </Popover>
        {historyButton}
      </div>
    );
  }

  const isOutdated = currentReview.status === "outdated";

  return (
    <div className="flex">
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            className={cn(
              "h-7 gap-1.5 text-xs",
              hasHistory && "rounded-r-none",
              isOutdated
                ? "border-amber-500 text-amber-700 dark:text-amber-400"
                : "border-emerald-500 text-emerald-700 dark:text-emerald-400",
            )}
          >
            {isOutdated ? (
              <Clock className="h-3.5 w-3.5" />
            ) : (
              <Check className="h-3.5 w-3.5" />
            )}
            {isOutdated
              ? t("carousel.review.outdated")
              : t("carousel.review.reviewed-by", {
                  name: currentReview.reviewer_name ?? currentReview.reviewed_by,
                })}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-72">
          <div className="space-y-3">
            {currentReview.note && (
              <p className="text-sm text-muted-foreground">
                {currentReview.note}
              </p>
            )}
            <p className="text-xs text-muted-foreground">
              {new Date(currentReview.reviewed_at).toLocaleString("cs")}
            </p>
            <div className="flex justify-end gap-2">
              <Button
                variant="ghost"
                size="sm"
                className="gap-1 text-destructive"
                onClick={handleRemove}
                disabled={deleteReview.isPending}
              >
                <X className="h-3.5 w-3.5" />
                {t("carousel.review.remove")}
              </Button>
              {isOutdated && (
                <Button
                  size="sm"
                  onClick={() => {
                    setNote("");
                    handleSubmit();
                  }}
                  disabled={createReview.isPending}
                >
                  {t("carousel.review.re-review")}
                </Button>
              )}
            </div>
          </div>
        </PopoverContent>
      </Popover>
      {historyButton}
    </div>
  );
}
