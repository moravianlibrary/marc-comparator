import { useTranslation } from "react-i18next";
import { Settings2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import type { Table } from "@tanstack/react-table";
import type { RecordSummary } from "../types";

interface ColumnConfigProps {
  table: Table<RecordSummary>;
  sortedColumnId?: string;
}

export function ColumnConfig({ table, sortedColumnId }: ColumnConfigProps) {
  const { t } = useTranslation("records");

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm">
          <Settings2 className="mr-2 h-4 w-4" />
          {t("table.column-config")}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[200px]" align="end">
        <div className="space-y-2">
          {table
            .getAllColumns()
            .filter((col) => col.getCanHide())
            .map((column) => {
              const isSortedColumn = column.id === sortedColumnId;
              return (
                <label key={column.id} className="flex items-center gap-2">
                  <Checkbox
                    checked={column.getIsVisible()}
                    disabled={isSortedColumn}
                    onCheckedChange={(checked) =>
                      column.toggleVisibility(!!checked)
                    }
                  />
                  <span className="text-sm">
                    {typeof column.columnDef.header === "string"
                      ? column.columnDef.header
                      : column.id}
                  </span>
                </label>
              );
            })}
        </div>
      </PopoverContent>
    </Popover>
  );
}
