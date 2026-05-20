import { useEffect, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ChevronLeft, ChevronRight } from "lucide-react";
import apiClient from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { useRecordFilters } from "../use-record-filters";
import type { MarcRecordData, SearchRecordsResponse } from "../types";
import { RecordHeader } from "./record-header";
import { MarcTable } from "./marc-table";

export function CarouselView() {
  const { t } = useTranslation("records");
  const { filters, setFilters, buildSearchPayload } = useRecordFilters();

  const payload = buildSearchPayload();
  const { data: searchData } = useQuery<SearchRecordsResponse>({
    queryKey: ["catalog-records", "search", payload],
    queryFn: () =>
      apiClient
        .post<SearchRecordsResponse>("/catalog-records/search", payload)
        .then((r) => r.data),
  });

  const records = searchData?.items ?? [];
  const currentIndex = records.findIndex((r) => r.id === filters.recordId);
  const currentRecord = currentIndex >= 0 ? records[currentIndex] : null;

  useEffect(() => {
    if (!filters.recordId && records.length > 0) {
      setFilters({ recordId: records[0].id } as any);
    }
  }, [records, filters.recordId, setFilters]);

  const [base, systemNumber] = filters.recordId
    ? [
        filters.recordId.substring(0, filters.recordId.indexOf("-")),
        filters.recordId.substring(filters.recordId.indexOf("-") + 1),
      ]
    : ["", ""];

  const { data: marcData, isLoading: marcLoading } = useQuery<MarcRecordData>({
    queryKey: ["catalog-records", "marc", base, systemNumber],
    queryFn: () =>
      apiClient
        .get<MarcRecordData>(
          `/catalog-records/${base}/${systemNumber}/marc`,
        )
        .then((r) => r.data),
    enabled: !!base && !!systemNumber,
  });

  const navigate = useCallback(
    (direction: "prev" | "next") => {
      if (currentIndex < 0) return;
      const nextIndex =
        direction === "prev" ? currentIndex - 1 : currentIndex + 1;
      if (nextIndex >= 0 && nextIndex < records.length) {
        setFilters({ recordId: records[nextIndex].id } as any);
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    },
    [currentIndex, records, setFilters],
  );

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "ArrowLeft") navigate("prev");
      if (e.key === "ArrowRight") navigate("next");
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [navigate]);

  if (!filters.recordId) {
    return (
      <p className="py-8 text-center text-muted-foreground">
        {t("carousel.no-record")}
      </p>
    );
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <Button
          variant="outline"
          size="sm"
          onClick={() => navigate("prev")}
          disabled={currentIndex <= 0}
        >
          <ChevronLeft className="mr-1 h-4 w-4" />
          {t("carousel.previous")}
        </Button>
        <span className="text-sm text-muted-foreground">
          {currentIndex >= 0 ? `${currentIndex + 1} / ${records.length}` : ""}
        </span>
        <Button
          variant="outline"
          size="sm"
          onClick={() => navigate("next")}
          disabled={currentIndex >= records.length - 1}
        >
          {t("carousel.next")}
          <ChevronRight className="ml-1 h-4 w-4" />
        </Button>
      </div>

      <div className="space-y-8">
        {currentRecord && <RecordHeader record={currentRecord} />}

        <section>
          <h2 className="mb-3 text-lg font-semibold">
            {t("carousel.marc-record")}
          </h2>
          {marcLoading ? (
            <p className="text-muted-foreground">{t("common:loading")}</p>
          ) : marcData ? (
            <MarcTable marc={marcData} />
          ) : (
            <p className="text-muted-foreground">-</p>
          )}
        </section>
      </div>
    </div>
  );
}
