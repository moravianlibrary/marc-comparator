import { z } from "zod";
import { CatalogRecordStateSchema } from "../../primitives/catalog_record";
import { ValidationSchema } from "./validation";
import { createEsResponseSchema } from "./es";
import { ComparisonSchema } from "./comparison";
import { AuthorityLinkSchema } from "./authority_link";

export const CatalogRecordSchema = z.object({
    base: z.string(),
    system_number: z.string(),
    type_of_record: z.string(),
    bibliographic_level: z.string(),
    title: z.string().default("Missing Title"),
    subtitle: z.string().optional(),
    authors: z.array(z.string()).default([]),
    last_sync: z.date(),
    state: z.array(CatalogRecordStateSchema),
    authority_links: z.array(AuthorityLinkSchema).default([]),
    comparisons: z.array(ComparisonSchema).default([]),
    validations: z.array(ValidationSchema).default([]),
});
export type CatalogRecord = z.infer<typeof CatalogRecordSchema>;

export const SearchCatalogRecordsResponseSchema = createEsResponseSchema(
    CatalogRecordSchema.partial()
);
export type SearchCatalogRecordsResponse = z.infer<
    typeof SearchCatalogRecordsResponseSchema
>;
