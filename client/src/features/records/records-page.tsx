import { useTranslation } from "react-i18next";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useRecordFilters } from "./use-record-filters";
import { PlotsView } from "./plots/plots-view";
import { TableView } from "./table/table-view";
import { CarouselView } from "./carousel/carousel-view";
import { AdditionView } from "./addition/addition-view";
import type { RecordTab } from "./types";

export function RecordsPage() {
  const { t } = useTranslation("records");
  const { filters, setTab } = useRecordFilters();

  return (
    <Tabs
      value={filters.tab}
      onValueChange={(v) => setTab(v as RecordTab)}
      className="space-y-4"
    >
      <TabsList>
        <TabsTrigger value="plots">{t("tabs.plots")}</TabsTrigger>
        <TabsTrigger value="table">{t("tabs.table")}</TabsTrigger>
        <TabsTrigger value="carousel">{t("tabs.carousel")}</TabsTrigger>
        <TabsTrigger value="addition">{t("tabs.addition")}</TabsTrigger>
      </TabsList>

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
    </Tabs>
  );
}
