import { z } from "zod";
import { CatalogRecordStateSchema } from "../../primitives/catalog_record";
import { ValidationResultSchema } from "./validation";
import { createEsResponseSchema } from "./es";
import { ComparisonResultSchema } from "./comparison";

export const AuthorityRecordIdSchema = z.object({
    base: z.string(),
    system_number: z.string(),
});
export type AuthorityRecordId = z.infer<typeof AuthorityRecordIdSchema>;

export const CatalogRecordSchema = z.object({
    base: z.string(),
    system_number: z.string(),
    last_sync: z.date(),
    state: z.array(CatalogRecordStateSchema),
    validation_results: z.array(ValidationResultSchema).default([]),
    authority_record_ids: z.array(AuthorityRecordIdSchema).default([]),
    comparison_results: z.array(ComparisonResultSchema).default([]),
});
export type CatalogRecord = z.infer<typeof CatalogRecordSchema>;

export const SearchCatalogRecordsResponseSchema = createEsResponseSchema(
    CatalogRecordSchema.partial()
);
export type SearchCatalogRecordsResponse = z.infer<
    typeof SearchCatalogRecordsResponseSchema
>;
