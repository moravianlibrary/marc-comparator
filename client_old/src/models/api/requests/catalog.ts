import { z } from "zod";

export const CatalogFetchRequestSchema = z.object({
    base: z.string(),
    system_number: z.string(),
});
export type CatalogFetchRequest = z.infer<typeof CatalogFetchRequestSchema>;

export const CatalogFetchBatchParamsSchema = z.object({
    base: z.string().optional(),
});
export type CatalogFetchBatchParams = z.infer<
    typeof CatalogFetchBatchParamsSchema
>;

export const CatalogSyncRequestSchema = z.object({
    base: z.string(),
    from_date: z.date().optional(),
});
export type CatalogSyncRequest = z.infer<typeof CatalogSyncRequestSchema>;
