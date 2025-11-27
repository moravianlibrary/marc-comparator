import { z } from "zod";

export const CatalogRecordStateSchema = z.enum([
    "Active",
    "Deleted",
    "Visible",
    "Hidden",
]);
export type CatalogRecordState = z.infer<typeof CatalogRecordStateSchema>;
