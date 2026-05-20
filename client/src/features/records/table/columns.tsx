import type { ColumnDef } from "@tanstack/react-table";
import { Badge } from "@/components/ui/badge";
import type { RecordSummary } from "../types";
import { RecordActions } from "./record-actions";

export function createColumns(
  t: (key: string) => string,
): ColumnDef<RecordSummary>[] {
  return [
    {
      accessorKey: "base",
      header: t("records:table.columns.base"),
      size: 80,
    },
    {
      accessorKey: "system_number",
      header: t("records:table.columns.system-number"),
      size: 120,
    },
    {
      accessorKey: "title",
      header: t("records:table.columns.title"),
      size: 300,
      cell: ({ row }) => (
        <span className="block max-w-[300px] truncate">
          {row.original.title ?? "-"}
        </span>
      ),
    },
    {
      accessorKey: "state",
      header: t("records:table.columns.state"),
      size: 200,
      cell: ({ row }) => (
        <div className="flex flex-wrap gap-1">
          {row.original.state.map((s) => (
            <Badge key={s} variant="outline" className="text-xs">
              {t(`records:state.${s}`)}
            </Badge>
          ))}
        </div>
      ),
    },
    {
      accessorKey: "authority_links_count",
      header: t("records:table.columns.authority-links"),
      size: 100,
      cell: ({ row }) => row.original.authority_links_count || "-",
    },
    {
      accessorKey: "comparisons_count",
      header: t("records:table.columns.comparisons"),
      size: 100,
      cell: ({ row }) => row.original.comparisons_count || "-",
    },
    {
      accessorKey: "validations_count",
      header: t("records:table.columns.validations"),
      size: 100,
      cell: ({ row }) => row.original.validations_count || "-",
    },
    {
      accessorKey: "latest_sync",
      header: t("records:table.columns.latest-sync"),
      size: 160,
      cell: ({ row }) =>
        row.original.latest_sync
          ? new Date(row.original.latest_sync).toLocaleString("cs-CZ")
          : "-",
    },
    {
      id: "actions",
      size: 60,
      cell: ({ row }) => <RecordActions record={row.original} />,
    },
  ];
}
