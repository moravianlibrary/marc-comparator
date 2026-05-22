import { useTranslation } from "react-i18next";
import { Settings2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  SECTION_GROUPS,
  type ChartId,
} from "./use-section-visibility";

interface SectionConfigProps {
  isVisible: (chartId: ChartId) => boolean;
  toggleChart: (chartId: ChartId) => void;
  isSectionVisible: (section: keyof typeof SECTION_GROUPS) => boolean;
  toggleSection: (section: keyof typeof SECTION_GROUPS) => void;
}

const CHART_LABEL_KEYS: Record<ChartId, string> = {
  base: "facet-fields.base",
  validators: "facet-fields.validators",
  authority_link_linkers: "facet-fields.authority_link_linkers",
  record_status: "plots.record-status",
  match_quality: "facet-fields.match_qualities",
  validation_status: "facet-fields.validation_statuses",
  type_of_record: "facet-fields.type_of_record",
  bibliographic_level: "facet-fields.bibliographic_level",
  authority_link_bases: "facet-fields.authority_link_bases",
  overall_score: "facet-fields.overall_score",
  field_explanations: "facet-fields.field_explanations",
  validation_reasons: "facet-fields.validation_reasons",
};

export function SectionConfig({ isVisible, toggleChart, isSectionVisible, toggleSection }: SectionConfigProps) {
  const { t } = useTranslation("records");

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm">
          <Settings2 className="mr-2 h-4 w-4" />
          {t("plots.section-config")}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[300px]" align="end">
        <div className="space-y-3">
          {(Object.entries(SECTION_GROUPS) as [keyof typeof SECTION_GROUPS, readonly ChartId[]][]).map(
            ([section, chartIds]) => (
              <div key={section}>
                {section === "context" ? (
                  <label className="flex items-center gap-2">
                    <Checkbox
                      checked={isSectionVisible("context")}
                      onCheckedChange={() => toggleSection("context")}
                    />
                    <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      {t(`plots.sections.${section}`)}
                    </span>
                  </label>
                ) : (
                  <>
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">
                      {t(`plots.sections.${section}`)}
                    </p>
                    <div className="space-y-1">
                      {chartIds.map((chartId) => (
                        <label key={chartId} className="flex items-center gap-2">
                          <Checkbox
                            checked={isVisible(chartId)}
                            onCheckedChange={() => toggleChart(chartId)}
                          />
                          <span className="text-sm">{t(CHART_LABEL_KEYS[chartId])}</span>
                        </label>
                      ))}
                    </div>
                  </>
                )}
              </div>
            ),
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}
