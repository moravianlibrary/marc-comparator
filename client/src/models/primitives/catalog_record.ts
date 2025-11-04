import { z } from "zod";

export const CatalogRecordStateSchema = z.enum([
    "Active",
    "Hidden",
    "Deleted",
    "Valid",
    "Invalid",
]);
export type CatalogRecordState = z.infer<typeof CatalogRecordStateSchema>;
