import z from "zod";

export const EsPerPageConfigSchema = z.object({
    options: z.array(z.number().min(1)).min(1),
    default: z.number().min(1),
});
export type EsPerPageConfig = z.infer<typeof EsPerPageConfigSchema>;

export const EsSearchConfigSchema = z.object({
    fields: z.array(z.string()).min(1),
    phraseBoosts: z.record(z.string(), z.number()).optional(),
    prefixBoosts: z.record(z.string(), z.number()).optional(),
    fuzzyBoosts: z.record(z.string(), z.number()).optional(),
});

export const EsTermsFilterConfigSchema = z.object({
    type: z.literal("terms"),
    include: z.union([z.array(z.string()), z.string()]).optional(),
    exclude: z.union([z.array(z.string()), z.string()]).optional(),
    order: z.enum(["asc", "desc"]).optional(),
    size: z.number().min(2).default(10),
    nested: z.boolean().optional(),
});
export type EsTermsFilterConfig = z.infer<typeof EsTermsFilterConfigSchema>;

export const EsRangeFilterConfigSchema = z.object({
    type: z.literal("range"),
    min: z.number().optional(),
    max: z.number().optional(),
    nested: z.boolean().optional(),
});
export type EsRangeFilterConfig = z.infer<typeof EsRangeFilterConfigSchema>;

export const EsHistogramFilterConfigSchema = z.object({
    type: z.literal("histogram"),
    interval: z.number(),
    min: z.number().optional(),
    max: z.number().optional(),
    coef: z.number().optional(),
    nested: z.boolean().optional(),
});
export type EsHistogramFilterConfig = z.infer<
    typeof EsHistogramFilterConfigSchema
>;

export const EsDateRangeFilterConfigSchema = z.object({
    type: z.literal("date-range"),
    nested: z.boolean().optional(),
});
export type EsDateRangeFilterConfig = z.infer<
    typeof EsDateRangeFilterConfigSchema
>;

export const EsFilterConfigSchema = z.union([
    EsTermsFilterConfigSchema,
    EsRangeFilterConfigSchema,
    EsHistogramFilterConfigSchema,
    EsDateRangeFilterConfigSchema,
]);
export type EsFilterConfig = z.infer<typeof EsFilterConfigSchema>;

export const EsSortByConfigSchema = z.array(
    z.record(
        z.string(),
        z.object({
            order: z.enum(["asc", "desc"]),
            mode: z.enum(["min", "max", "sum", "avg", "median"]).optional(),
            nested: z
                .object({
                    path: z.string(),
                    filter: z.record(z.string(), z.any()).optional(),
                })
                .optional(),
        })
    )
);
export type EsSortByConfig = z.infer<typeof EsSortByConfigSchema>;

export const EsConfigSchema = z.object({
    columnFields: z.record(z.string(), z.array(z.string())).optional(),
    perPage: EsPerPageConfigSchema,
    search: EsSearchConfigSchema.optional(),
    filters: z.record(z.string(), EsFilterConfigSchema).optional(),
    sortBy: z.record(z.string(), EsSortByConfigSchema).optional(),
});
export type EsConfig = z.infer<typeof EsConfigSchema>;

export const EsTermsFilterStateSchema = z.object({
    size: z.number().min(2).optional(),
    include: z.preprocess((val) => {
        if (typeof val === "string") return val.split(",");
        return val;
    }, z.array(z.string()).optional()),
});
export type EsTermsFilterState = z.infer<typeof EsTermsFilterStateSchema>;

export const EsRangeFilterStateSchema = z.object({
    gte: z.number().optional(),
    lte: z.number().optional(),
});
export type EsRangeFilterState = z.infer<typeof EsRangeFilterStateSchema>;

export const EsHistogramFilterStateSchema = z.object({
    gte: z.number().optional(),
    lte: z.number().optional(),
});
export type EsHistogramFilterState = z.infer<
    typeof EsHistogramFilterStateSchema
>;

export const EsDateRangeFilterStateSchema = z.object({
    gte: z.string().optional(),
    lte: z.string().optional(),
});
export type EsDateRangeFilterState = z.infer<
    typeof EsDateRangeFilterStateSchema
>;

export const EsFilterStateSchema = z.union([
    EsTermsFilterStateSchema,
    EsRangeFilterStateSchema,
    EsHistogramFilterStateSchema,
    EsDateRangeFilterStateSchema,
]);
export type EsFilterState = z.infer<typeof EsFilterStateSchema>;

export const EsStateSchema = z.object({
    config: EsConfigSchema,
    columns: z.record(
        z.string(),
        z.object({
            order: z.number().min(0),
            visible: z.boolean(),
        })
    ),
    page: z.number().min(1).default(1).meta({ url: true }),
    perPage: z.number().min(1).default(10).meta({ url: true }),
    sortBy: z.string().optional().meta({ url: true }),
    searchTerm: z
        .preprocess(
            (val) => (typeof val === "string" ? val : String(val || "")),
            z.string().optional()
        )
        .meta({ url: true }),
    searchFuzziness: z.string().optional().meta({ url: true }),
    terms: z
        .record(z.string().meta({ url: true }), EsTermsFilterStateSchema)
        .optional()
        .meta({
            url: true,
        }),
    range: z.record(z.string(), EsRangeFilterStateSchema).optional().meta({
        url: true,
    }),
    hist: z
        .record(z.string(), EsHistogramFilterStateSchema)
        .optional()
        .meta({ url: true }),
    dateRange: z
        .record(z.string(), EsDateRangeFilterStateSchema)
        .optional()
        .meta({ url: true }),
    selectedIds: z
        .preprocess((val) => {
            if (val instanceof Set) return val;
            if (typeof val === "string") {
                return new Set(val.split(",").filter(Boolean));
            }
            if (Array.isArray(val)) {
                return new Set(val);
            }
            if (val && typeof val === "object") {
                return new Set(Object.keys(val));
            }
            return new Set();
        }, z.set(z.string()))
        .default(new Set()),
    isAllSelected: z.boolean().default(false),
});
export type EsState = z.infer<typeof EsStateSchema>;

export type EsStateAction =
    | { type: "setColumnOrder"; columnKeys: string[] }
    | { type: "toggleColumnVisibility"; columnKey: string }
    | { type: "setPaginationParams"; page: number; perPage: number }
    | { type: "setSearchTerm"; value: string }
    | { type: "toggleTerm"; field: string; bucketKey: string }
    | { type: "changeTermBucketSize"; field: string; size: number }
    | { type: "setRange"; field: string; gte?: number; lte?: number }
    | { type: "setHistogramRange"; field: string; gte?: number; lte?: number }
    | { type: "setDateRange"; field: string; gte?: string; lte?: string }
    | { type: "setFieldQuery"; field: string; query: string }
    | { type: "clearFilters"; field?: string }
    | { type: "setSortBy"; sortBy: string }
    | { type: "toggleSelection"; id: string; pageIds: string[] }
    | { type: "selectPage"; pageIds: string[] }
    | { type: "selectAll" }
    | { type: "clearSelection" };
