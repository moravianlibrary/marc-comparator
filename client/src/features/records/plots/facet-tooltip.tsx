import { useTranslation } from "react-i18next";

interface FacetTooltipProps {
  active?: boolean;
  payload?: any[];
  nameKey?: string;
  countKey?: string;
  previewKey?: string;
}

export function FacetTooltip({
  active,
  payload,
  nameKey = "name",
  countKey = "count",
  previewKey = "preview",
}: FacetTooltipProps) {
  const { t } = useTranslation();

  if (!active || !payload?.length) return null;

  const item = payload[0];
  const data = item.payload;
  const name = data[nameKey] ?? item.name;
  const count = data[countKey] ?? item.value;
  const preview = data[previewKey];
  const color = data.fill ?? item.color;

  return (
    <div className="grid min-w-[8rem] items-start gap-1.5 rounded-lg border border-border/50 bg-background px-2.5 py-1.5 text-xs shadow-xl">
      <div className="font-medium">{name}</div>
      <div className="grid gap-1.5">
        <div className="flex w-full items-stretch gap-2">
          <div className="shrink-0 rounded-[2px] w-1" style={{ backgroundColor: color }} />
          <div className="flex flex-1 justify-between items-center leading-none">
            <span className="text-muted-foreground">{t("common:chart.count")}</span>
            <span className="font-mono font-medium text-foreground tabular-nums">
              {typeof count === "number" ? count.toLocaleString() : count}
            </span>
          </div>
        </div>
        {preview != null && preview > 0 && (
          <div className="flex w-full items-stretch gap-2">
            <div
              className="shrink-0 rounded-[2px] w-1"
              style={{
                backgroundColor: "color-mix(in oklch, var(--muted-foreground) 15%, transparent)",
              }}
            />
            <div className="flex flex-1 justify-between items-center leading-none">
              <span className="text-muted-foreground">{t("common:chart.preview")}</span>
              <span className="font-mono font-medium text-foreground tabular-nums">
                {preview.toLocaleString()}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
