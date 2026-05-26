import { useMemo, useState, useEffect } from "react";
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  type SortingState,
} from "@tanstack/react-table";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Info, X } from "lucide-react";
import apiClient from "@/lib/api-client";
import { useHasPermission } from "@/hooks/use-permissions";
import { Permission } from "@/types/permission";

import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useRecordFilters } from "../use-record-filters";
import type { SearchRecordsResponse } from "../types";
import { RecordTaskActions, AdvancedTaskActions } from "../record-task-actions";
import { createColumns } from "./columns";
import { ColumnConfig } from "./column-config";

const PAGE_SIZES = [10, 25, 50, 100, 1000];

export function TableView() {
  const { t } = useTranslation();
  const { hasPermission } = useHasPermission();
  const canProcess = hasPermission(Permission.ProcessRecords);
  const canRunPartial = hasPermission(Permission.RunPartialRecordTasks);
  const { filters, setFilters, setPage, setSearch, buildSearchPayload, buildRecordFilter } =
    useRecordFilters();

  const [searchInput, setSearchInput] = useState(filters.search);

  useEffect(() => {
    if (searchInput === filters.search) return;
    const timeout = setTimeout(() => setSearch(searchInput), 300);
    return () => clearTimeout(timeout);
  }, [searchInput, filters.search, setSearch]);

  useEffect(() => {
    setSearchInput(filters.search);
  }, [filters.search]);

  const payload = buildSearchPayload();

  const { data, isLoading } = useQuery<SearchRecordsResponse>({
    queryKey: ["catalog-records", "search", payload],
    queryFn: () =>
      apiClient
        .post<SearchRecordsResponse>("/catalog-records/search", payload)
        .then((r) => r.data),
  });

  const onNavigate = useMemo(
    () => (rowIndex: number, viewKey: string) => {
      setFilters({ tab: "carousel", recordIndex: rowIndex, carouselView: viewKey });
    },
    [setFilters],
  );

  const sorting: SortingState = useMemo(
    () => [{ id: filters.sortBy, desc: filters.sortOrder === "desc" }],
    [filters.sortBy, filters.sortOrder],
  );

  const columns = useMemo(() => createColumns(t, onNavigate), [t, onNavigate]);

  const totalPages = data ? Math.ceil(data.total / filters.pageSize) : 0;

  const table = useReactTable({
    data: data?.items ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
    manualSorting: true,
    enableSortingRemoval: false,
    pageCount: totalPages,
    state: {
      pagination: {
        pageIndex: filters.page - 1,
        pageSize: filters.pageSize,
      },
      sorting,
    },
    onSortingChange: (updater) => {
      const next = typeof updater === "function" ? updater(sorting) : updater;
      if (next.length > 0) {
        setFilters({
          sortBy: next[0].id as typeof filters.sortBy,
          sortOrder: next[0].desc ? "desc" : "asc",
          page: 1,
        });
      }
    },
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        {filters.recordId && (
          <Badge
            variant="secondary"
            className="gap-1 cursor-pointer shrink-0"
            onClick={() => setFilters({ recordId: "", recordIndex: 0 })}
          >
            <span className="text-muted-foreground">
              {t("records:plots.record-id")}:
            </span>{" "}
            {filters.recordId}
            <X className="h-3 w-3" />
          </Badge>
        )}
        <div className="flex items-center gap-1.5 max-w-sm flex-1">
          <Input
            placeholder={t("records:table.search-placeholder")}
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
          <Popover>
            <PopoverTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0">
                <Info className="h-4 w-4 text-muted-foreground" />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[320px]" align="start">
              <div className="space-y-3">
                <p className="font-medium text-sm">{t("records:table.search-help.title")}</p>
                <div className="space-y-2 text-sm">
                  <div>
                    <p className="font-medium">{t("records:table.search-help.exact-match")}</p>
                    <p className="text-muted-foreground">{t("records:table.search-help.exact-match-desc")}</p>
                  </div>
                  <div>
                    <p className="font-medium">{t("records:table.search-help.text-search")}</p>
                    <p className="text-muted-foreground">{t("records:table.search-help.text-search-desc")}</p>
                  </div>
                </div>
              </div>
            </PopoverContent>
          </Popover>
        </div>

        <div className="flex-1" />

        {(canProcess || canRunPartial) && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground whitespace-nowrap">{t("records:table.bulk-actions")}</span>
            {canProcess && <RecordTaskActions filters={buildRecordFilter()} />}
            {canRunPartial && <AdvancedTaskActions filters={buildRecordFilter()} />}
          </div>
        )}

        <ColumnConfig table={table} sortedColumnId={filters.sortBy} />
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  const canSort = header.column.getCanSort();
                  const sorted = header.column.getIsSorted();
                  return (
                    <TableHead
                      key={header.id}
                      style={{ width: header.getSize() }}
                      className={canSort ? "cursor-pointer select-none" : undefined}
                      onClick={canSort ? header.column.getToggleSortingHandler() : undefined}
                    >
                      <div className="flex items-center gap-1">
                        {header.isPlaceholder
                          ? null
                          : flexRender(
                              header.column.columnDef.header,
                              header.getContext(),
                            )}
                        {sorted === "asc" && " \u2191"}
                        {sorted === "desc" && " \u2193"}
                        {canSort && !sorted && (
                          <span className="text-muted-foreground/40">{" \u2195"}</span>
                        )}
                      </div>
                    </TableHead>
                  );
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={columns.length} className="text-center">
                  {t("common:loading")}
                </TableCell>
              </TableRow>
            ) : table.getRowModel().rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={columns.length} className="text-center">
                  {t("common:no-data")}
                </TableCell>
              </TableRow>
            ) : (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  className="cursor-pointer"
                  onClick={() => setFilters({ tab: "carousel", recordIndex: row.index })}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext(),
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <p className="text-sm text-muted-foreground">
            {data
              ? t("common:pagination.page", {
                  page: filters.page,
                  total: totalPages,
                })
              : ""}
          </p>
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-muted-foreground">{t("records:table.page-size")}</span>
            <Select
              value={String(filters.pageSize)}
              onValueChange={(val) => setFilters({ pageSize: Number(val), page: 1 })}
            >
              <SelectTrigger className="h-8 w-fit">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PAGE_SIZES.map((size) => (
                  <SelectItem key={size} value={String(size)}>
                    {size}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage(filters.page - 1)}
            disabled={filters.page <= 1}
          >
            {t("common:pagination.previous")}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage(filters.page + 1)}
            disabled={filters.page >= totalPages}
          >
            {t("common:pagination.next")}
          </Button>
        </div>
      </div>
    </div>
  );
}
