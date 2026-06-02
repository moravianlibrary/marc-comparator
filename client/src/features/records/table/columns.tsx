import type { ColumnDef } from "@tanstack/react-table";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { STATE_COLORS, type RecordSummary } from "../types";
import { groupValidations, VALIDATION_BADGE_CLASS, COMPARISON_BADGE_CLASS } from "../utils";

/** Column IDs that the backend can sort by. */
const SORTABLE_COLUMNS = new Set(["base", "system_number", "latest_sync", "comparison_score"]);

export function createColumns(
  t: (key: string) => string,
  onNavigate?: (rowIndex: number, viewKey: string) => void,
): ColumnDef<RecordSummary>[] {
  return [
    {
      accessorKey: "base",
      header: t("records:table.columns.base"),
      size: 80,
      enableSorting: SORTABLE_COLUMNS.has("base"),
    },
    {
      accessorKey: "system_number",
      header: t("records:table.columns.system-number"),
      size: 120,
      enableSorting: SORTABLE_COLUMNS.has("system_number"),
    },
    {
      accessorKey: "title",
      header: t("records:table.columns.title"),
      size: 300,
      enableSorting: false,
      cell: ({ row }) => (
        <span className="block max-w-[300px] truncate">{row.original.title ?? "-"}</span>
      ),
    },
    {
      accessorKey: "authors",
      header: t("records:table.columns.authors"),
      size: 200,
      enableSorting: false,
      cell: ({ row }) => {
        const authors = row.original.authors;
        if (authors.length === 0) return "-";
        return <span className="block max-w-[200px] truncate">{authors.join(", ")}</span>;
      },
    },
    {
      accessorKey: "state",
      header: t("records:table.columns.state"),
      size: 200,
      enableSorting: false,
      cell: ({ row }) => (
        <div className="flex flex-wrap gap-1">
          {row.original.state.map((s) => (
            <Badge key={s} variant="outline" className={cn("text-xs", STATE_COLORS[s])}>
              {t(`records:state.${s}`)}
            </Badge>
          ))}
        </div>
      ),
    },
    {
      id: "authority_links",
      header: t("records:table.columns.authority-links"),
      size: 120,
      enableSorting: false,
      cell: ({ row }) => {
        const links = row.original.authority_links;
        if (links.length === 0) return "-";
        return (
          <div className="flex flex-wrap gap-1">
            {links.map((al) => {
              const systemNumber = al.authority_record_id.startsWith(al.base + "-")
                ? al.authority_record_id.slice(al.base.length + 1)
                : al.authority_record_id;
              const viewKey = `auth:${al.base}:${systemNumber}`;
              return (
                <Badge
                  key={`${al.linker}-${al.base}`}
                  variant="outline"
                  className={cn("text-xs", onNavigate && "cursor-pointer hover:bg-accent")}
                  onClick={
                    onNavigate
                      ? (e) => {
                          e.stopPropagation();
                          onNavigate(row.index, viewKey);
                        }
                      : undefined
                  }
                >
                  {al.base}
                </Badge>
              );
            })}
          </div>
        );
      },
    },
    {
      id: "comparison_score",
      header: t("records:table.columns.comparisons"),
      size: 140,
      enableSorting: SORTABLE_COLUMNS.has("comparison_score"),
      cell: ({ row }) => {
        const comps = row.original.comparisons;
        if (comps.length === 0) return "-";
        return (
          <div className="flex flex-wrap gap-1">
            {comps.map((c) => {
              const viewKey = `comp:${c.comparator}:${c.other_record_id}`;
              return (
                <Badge
                  key={`${c.comparator}-${c.other_record_id}`}
                  variant="outline"
                  className={cn(
                    "text-xs",
                    COMPARISON_BADGE_CLASS[c.match_quality],
                    onNavigate && "cursor-pointer hover:bg-accent",
                  )}
                  onClick={
                    onNavigate
                      ? (e) => {
                          e.stopPropagation();
                          onNavigate(row.index, viewKey);
                        }
                      : undefined
                  }
                >
                  {c.base}: {(c.overall_score * 100).toFixed(0)}%
                </Badge>
              );
            })}
          </div>
        );
      },
    },
    {
      id: "validations",
      header: t("records:table.columns.validations"),
      size: 140,
      enableSorting: false,
      cell: ({ row }) => {
        const vals = row.original.validations;
        if (vals.length === 0) return "-";
        return (
          <div className="flex flex-wrap gap-1">
            {groupValidations(vals).map((g) => {
              const viewKey = `val:${g.validator}`;
              return (
                <Badge
                  key={`${g.validator}-${g.target_tag}-${g.status}`}
                  variant="outline"
                  className={cn(
                    "text-xs",
                    VALIDATION_BADGE_CLASS[g.status],
                    onNavigate && "cursor-pointer hover:bg-accent",
                  )}
                  onClick={
                    onNavigate
                      ? (e) => {
                          e.stopPropagation();
                          onNavigate(row.index, viewKey);
                        }
                      : undefined
                  }
                >
                  {t(`records:validator-name.${g.validator}`)} [{g.target_tag}]:{" "}
                  {t(`records:validity-status.${g.status}`)}
                  {g.count > 1 && (
                    <span className="ml-1 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-muted-foreground/20 px-1 text-[10px] font-medium">
                      {g.count}
                    </span>
                  )}
                </Badge>
              );
            })}
          </div>
        );
      },
    },
    {
      accessorKey: "latest_sync",
      header: t("records:table.columns.latest-sync"),
      size: 160,
      enableSorting: SORTABLE_COLUMNS.has("latest_sync"),
      cell: ({ row }) =>
        row.original.latest_sync ? new Date(row.original.latest_sync).toLocaleString("cs-CZ") : "-",
    },
  ];
}
