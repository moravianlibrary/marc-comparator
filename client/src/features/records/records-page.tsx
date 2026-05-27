import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { CircleHelp } from "lucide-react";
import apiClient from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  TypographyP,
  TypographyList,
} from "@/components/ui/typography";
import { useRecordFilters } from "./use-record-filters";
import { PlotsView } from "./plots/plots-view";
import { TableView } from "./table/table-view";
import { CarouselView } from "./carousel/carousel-view";
import { AdditionView } from "./addition/addition-view";
import type { RecordTab, SearchRecordsResponse } from "./types";

function countActiveFilters(filters: ReturnType<typeof useRecordFilters>["filters"]): number {
  let count = 0;
  if (filters.bases.length) count++;
  if (filters.typeOfRecord.length) count++;
  if (filters.bibliographicLevel.length) count++;
  if (filters.reviewStatuses.length) count++;
  if (filters.deleted) count++;
  if (filters.processed) count++;
  if (filters.authorityLinkLinkers.length) count++;
  if (filters.authorityLinkBases.length) count++;
  if (filters.comparisonBases.length) count++;
  if (filters.matchQualities.length) count++;
  if (filters.fieldExplanations.length) count++;
  if (filters.validators.length) count++;
  if (filters.validationStatuses.length) count++;
  if (filters.validationTargetTags.length) count++;
  if (filters.scoreMin > 0) count++;
  if (filters.scoreMax < 1) count++;
  if (filters.recordId) count++;
  return count;
}

export function RecordsPage() {
  const { t } = useTranslation("records");
  const { filters, setTab, buildSearchPayload } = useRecordFilters();
  const [showHelp, setShowHelp] = useState(false);

  const payload = buildSearchPayload();
  const { data: searchData } = useQuery<SearchRecordsResponse>({
    queryKey: ["catalog-records", "search", payload],
    queryFn: () =>
      apiClient
        .post<SearchRecordsResponse>("/catalog-records/search", payload)
        .then((r) => r.data),
  });

  const activeFilterCount = countActiveFilters(filters);
  const totalResults = searchData?.total;
  const records = searchData?.items ?? [];
  const resolvedIndex = records.length > 0
    ? (filters.page - 1) * filters.pageSize + Math.min(filters.recordIndex, records.length - 1)
    : null;

  return (
    <Tabs
      value={filters.tab}
      onValueChange={(v) => setTab(v as RecordTab)}
      className="space-y-4"
    >
      <div className="flex items-center gap-2">
        <TabsList>
          <TabsTrigger value="plots">
            {t("tabs.plots")}
            {activeFilterCount > 0 && (
              <span className="ml-1.5 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-primary px-1.5 text-[11px] font-medium text-primary-foreground">
                {activeFilterCount}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="table">
            {t("tabs.table")}
            {totalResults != null && (
              <span className="ml-1.5 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-accent-foreground px-1.5 text-[11px] font-medium text-accent">
                {totalResults}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="carousel">
            {t("tabs.carousel")}
            {resolvedIndex != null && totalResults != null && totalResults > 0 && (
              <span className="ml-1.5 inline-flex h-5 items-center justify-center rounded-full bg-accent-foreground px-1.5 text-[11px] font-medium text-accent">
                {resolvedIndex + 1} / {totalResults}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="addition">{t("tabs.addition")}</TabsTrigger>
        </TabsList>
        <Button
          variant="ghost"
          size="sm"
          className="gap-1.5 text-muted-foreground"
          onClick={() => setShowHelp(true)}
        >
          <CircleHelp className="h-4 w-4" />
          {t(`help.${filters.tab}.button`)}
        </Button>
      </div>

      <TabsContent value="plots">
        <PlotsView />
      </TabsContent>
      <TabsContent value="table">
        <TableView />
      </TabsContent>
      <TabsContent value="carousel">
        <CarouselView />
      </TabsContent>
      <TabsContent value="addition">
        <AdditionView />
      </TabsContent>

      <Dialog open={showHelp} onOpenChange={setShowHelp}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{t(`help.${filters.tab}.title`)}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <TypographyP>{t(`help.${filters.tab}.description`)}</TypographyP>
            <TypographyList>
              {(t(`help.${filters.tab}.actions`, { returnObjects: true }) as string[]).map(
                (action) => (
                  <li key={action}>{action}</li>
                ),
              )}
            </TypographyList>
          </div>
        </DialogContent>
      </Dialog>
    </Tabs>
  );
}
