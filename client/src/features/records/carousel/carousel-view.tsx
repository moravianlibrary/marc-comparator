import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import apiClient from "@/lib/api-client";
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  CarouselNext,
  CarouselPrevious,
  type CarouselApi,
} from "@/components/ui/carousel";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { useRecordFilters } from "../use-record-filters";
import type {
  MarcRecordData,
  SearchRecordsResponse,
  ComparisonDetail,
  ValidationDetail,
  RecordSummary,
} from "../types";
import type { AnnotationType } from "./marc-table";
import { RecordHeader } from "./record-header";
import { MarcTable } from "./marc-table";

type ViewOption =
  | { kind: "marc" }
  | { kind: "authority"; base: string; systemNumber: string }
  | { kind: "comparison"; comparisonIdx: number }
  | { kind: "validation"; validatorName: string };

function parseViewKey(key: string): ViewOption {
  if (key.startsWith("auth:")) {
    const rest = key.slice(5);
    const sepIdx = rest.indexOf(":");
    return { kind: "authority", base: rest.slice(0, sepIdx), systemNumber: rest.slice(sepIdx + 1) };
  }
  if (key.startsWith("comp:")) {
    return { kind: "comparison", comparisonIdx: parseInt(key.slice(5), 10) };
  }
  if (key.startsWith("val:")) {
    return { kind: "validation", validatorName: key.slice(4) };
  }
  return { kind: "marc" };
}

function buildAuthorityKey(base: string, authorityRecordId: string): string {
  const systemNumber = authorityRecordId.startsWith(base + "-")
    ? authorityRecordId.slice(base.length + 1)
    : authorityRecordId;
  return `auth:${base}:${systemNumber}`;
}

function isViewAvailable(
  key: string,
  record: RecordSummary,
  comparisons: ComparisonDetail[] | undefined,
  validations: ValidationDetail[] | undefined,
): boolean {
  if (key === "marc") return true;
  const opt = parseViewKey(key);
  switch (opt.kind) {
    case "marc":
      return true;
    case "authority":
      return record.authority_links.some(
        (al) => buildAuthorityKey(al.base, al.authority_record_id) === key,
      );
    case "comparison":
      return !!comparisons && opt.comparisonIdx < comparisons.length;
    case "validation":
      return !!validations && validations.some((v) => v.validator === opt.validatorName);
  }
}

export function CarouselView() {
  const { t } = useTranslation("records");
  const { filters, setFilters, buildSearchPayload } = useRecordFilters();
  const [selectedView, setSelectedView] = useState<string>("marc");
  const [targetFieldsOnly, setTargetFieldsOnly] = useState(false);
  const [api, setApi] = useState<CarouselApi>();
  const prevRef = useRef<HTMLButtonElement>(null);
  const nextRef = useRef<HTMLButtonElement>(null);

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

  // Auto-select first record
  useEffect(() => {
    if (!filters.recordId && records.length > 0) {
      setFilters({ recordId: records[0].id } as any);
    }
  }, [records, filters.recordId, setFilters]);

  // Sync carousel position when currentIndex changes (e.g. from table click)
  useEffect(() => {
    if (api && currentIndex >= 0) {
      api.scrollTo(currentIndex, true);
    }
  }, [api, currentIndex]);

  // Listen to carousel slide changes and update record filter
  useEffect(() => {
    if (!api) return;

    const onSelect = () => {
      const idx = api.selectedScrollSnap();
      if (idx >= 0 && idx < records.length && records[idx].id !== filters.recordId) {
        setFilters({ recordId: records[idx].id } as any);
      }
    };

    api.on("select", onSelect);
    return () => { api.off("select", onSelect); };
  }, [api, records, filters.recordId, setFilters]);

  // Shift focus to the other arrow when one becomes disabled at edges
  useEffect(() => {
    if (!api) return;

    const handleFocus = () => {
      setTimeout(() => {
        const active = document.activeElement;
        if (prevRef.current?.disabled && (active === prevRef.current || active === document.body)) {
          nextRef.current?.focus();
        } else if (nextRef.current?.disabled && (active === nextRef.current || active === document.body)) {
          prevRef.current?.focus();
        }
      }, 0);
    };

    api.on("select", handleFocus);
    return () => { api.off("select", handleFocus); };
  }, [api]);

  // Auto-focus a non-disabled navigation button when entering the carousel tab
  useEffect(() => {
    if (!api) return;
    const timer = setTimeout(() => {
      if (api.canScrollNext()) {
        nextRef.current?.focus();
      } else if (api.canScrollPrev()) {
        prevRef.current?.focus();
      }
    }, 50);
    return () => clearTimeout(timer);
  }, [api]);

  const base = currentRecord?.base ?? "";
  const systemNumber = currentRecord?.system_number ?? "";

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

  const { data: comparisons, isFetching: comparisonsFetching } = useQuery<ComparisonDetail[]>({
    queryKey: ["catalog-records", "comparisons", base, systemNumber],
    queryFn: () =>
      apiClient
        .get<ComparisonDetail[]>(
          `/catalog-records/${base}/${systemNumber}/comparisons`,
        )
        .then((r) => r.data),
    enabled: !!base && !!systemNumber,
  });

  const { data: validations, isFetching: validationsFetching } = useQuery<ValidationDetail[]>({
    queryKey: ["catalog-records", "validations", base, systemNumber],
    queryFn: () =>
      apiClient
        .get<ValidationDetail[]>(
          `/catalog-records/${base}/${systemNumber}/validations`,
        )
        .then((r) => r.data),
    enabled: !!base && !!systemNumber,
  });

  // Resolve view option
  const viewOpt = parseViewKey(selectedView);

  // Fetch authority record MARC when an authority view is selected
  const authorityBase = viewOpt.kind === "authority" ? viewOpt.base : "";
  const authoritySystemNumber = viewOpt.kind === "authority" ? viewOpt.systemNumber : "";
  const { data: authorityMarcData, isLoading: authorityMarcLoading } = useQuery<MarcRecordData>({
    queryKey: ["catalog-records", "marc", authorityBase, authoritySystemNumber],
    queryFn: () =>
      apiClient
        .get<MarcRecordData>(
          `/catalog-records/${authorityBase}/${authoritySystemNumber}/marc`,
        )
        .then((r) => r.data),
    enabled: !!authorityBase && !!authoritySystemNumber,
  });

  // When switching records, keep selection if available, otherwise fall back to "marc"
  // Wait until comparisons/validations have finished loading before checking availability
  const prevRecordId = useRef(currentRecord?.id);
  useEffect(() => {
    if (!currentRecord || currentRecord.id === prevRecordId.current) return;
    if (comparisonsFetching || validationsFetching) return;
    prevRecordId.current = currentRecord.id;
    if (selectedView !== "marc" && !isViewAvailable(selectedView, currentRecord, comparisons, validations)) {
      setSelectedView("marc");
      setTargetFieldsOnly(false);
    }
  }, [currentRecord, comparisons, validations, selectedView, comparisonsFetching, validationsFetching]);

  // Build authority link options
  const authorityOptions = currentRecord?.authority_links.map((al) => ({
    key: buildAuthorityKey(al.base, al.authority_record_id),
    label: `${al.base} - ${al.authority_record_id}`,
  })) ?? [];

  // Build comparison options
  const comparisonOptions = (comparisons ?? []).map((c, i) => ({
    key: `comp:${i}`,
    label: `${c.comparator} → ${c.base}`,
  }));

  // Build validation options (deduplicated by validator name)
  const validatorNames = [...new Set((validations ?? []).map((v) => v.validator))];
  const validationOptions = validatorNames.map((name) => ({
    key: `val:${name}`,
    label: name,
  }));

  const hasOptions = authorityOptions.length > 0 || comparisonOptions.length > 0 || validationOptions.length > 0;

  // Resolve annotation data for MarcTable
  let annotationType: AnnotationType | undefined;
  let comparisonAnnotations = undefined;
  let validationAnnotations = undefined;

  if (viewOpt.kind === "comparison" && comparisons && viewOpt.comparisonIdx < comparisons.length) {
    annotationType = "comparison";
    comparisonAnnotations = comparisons[viewOpt.comparisonIdx].result.field_results ?? undefined;
  } else if (viewOpt.kind === "validation" && validations) {
    annotationType = "validation";
    validationAnnotations = validations
      .filter((v) => v.validator === viewOpt.validatorName)
      .map((v) => v.result);
  }

  // Determine which MARC data and loading state to use
  const isAuthority = viewOpt.kind === "authority";
  const displayMarc = isAuthority ? authorityMarcData : marcData;
  const displayLoading = isAuthority ? authorityMarcLoading : marcLoading;

  // Determine target field tags for filtering
  const hasAnnotation = annotationType !== undefined;
  const targetTags = new Set<string>();
  if (targetFieldsOnly && hasAnnotation) {
    comparisonAnnotations?.forEach((a) => targetTags.add(a.tag));
    validationAnnotations?.forEach((a) => targetTags.add(a.target.tag));
  }

  if (!filters.recordId) {
    return (
      <p className="py-8 text-center text-muted-foreground">
        {t("carousel.no-record")}
      </p>
    );
  }

  return (
    <Carousel
      setApi={setApi}
      opts={{ startIndex: currentIndex >= 0 ? currentIndex : 0, watchDrag: false }}
      className="mx-12"
    >
      <CarouselContent>
        {records.map((record) => (
          <CarouselItem key={record.id}>
            {record.id === currentRecord?.id && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <RecordHeader record={record} />
                </div>

                <div className="flex items-center gap-4">
                  <Select value={selectedView} onValueChange={(v) => {
                    setSelectedView(v);
                    const opt = parseViewKey(v);
                    if (opt.kind !== "comparison" && opt.kind !== "validation") {
                      setTargetFieldsOnly(false);
                    }
                  }}>
                    <SelectTrigger className="w-[320px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="marc">{t("carousel.marc-record")}</SelectItem>

                      {authorityOptions.length > 0 && (
                        <>
                          <SelectSeparator />
                          <SelectGroup>
                            <SelectLabel>{t("carousel.authority-records")}</SelectLabel>
                            {authorityOptions.map((opt) => (
                              <SelectItem key={opt.key} value={opt.key}>
                                {opt.label}
                              </SelectItem>
                            ))}
                          </SelectGroup>
                        </>
                      )}

                      {comparisonOptions.length > 0 && (
                        <>
                          <SelectSeparator />
                          <SelectGroup>
                            <SelectLabel>{t("carousel.comparisons")}</SelectLabel>
                            {comparisonOptions.map((opt) => (
                              <SelectItem key={opt.key} value={opt.key}>
                                {opt.label}
                              </SelectItem>
                            ))}
                          </SelectGroup>
                        </>
                      )}

                      {validationOptions.length > 0 && (
                        <>
                          <SelectSeparator />
                          <SelectGroup>
                            <SelectLabel>{t("carousel.validations")}</SelectLabel>
                            {validationOptions.map((opt) => (
                              <SelectItem key={opt.key} value={opt.key}>
                                {opt.label}
                              </SelectItem>
                            ))}
                          </SelectGroup>
                        </>
                      )}
                    </SelectContent>
                  </Select>

                  {hasAnnotation && (
                    <div className="flex items-center gap-2">
                      <Checkbox
                        id="target-fields-only"
                        checked={targetFieldsOnly}
                        onCheckedChange={(checked) => setTargetFieldsOnly(checked === true)}
                      />
                      <Label htmlFor="target-fields-only" className="text-sm cursor-pointer">
                        {t("carousel.target-fields-only")}
                      </Label>
                    </div>
                  )}
                </div>

                {displayLoading ? (
                  <p className="text-muted-foreground">{t("common:loading")}</p>
                ) : displayMarc ? (
                  <MarcTable
                    marc={displayMarc}
                    annotationType={annotationType}
                    comparisonAnnotations={comparisonAnnotations}
                    validationAnnotations={validationAnnotations}
                    targetTags={targetFieldsOnly && targetTags.size > 0 ? targetTags : undefined}
                  />
                ) : (
                  <p className="text-muted-foreground">-</p>
                )}
              </div>
            )}
          </CarouselItem>
        ))}
      </CarouselContent>
      <CarouselPrevious ref={prevRef} className="fixed left-4 top-1/2" />
      <CarouselNext ref={nextRef} className="fixed right-4 top-1/2" />
    </Carousel>
  );
}
