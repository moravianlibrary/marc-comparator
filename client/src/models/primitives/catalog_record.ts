import { z } from "zod";

export const CatalogRecordStateSchema = z.enum([
    "Active",
    "Deleted",
    "Valid",
    "Invalid",
    "Hidden",
]);
export type CatalogRecordState = z.infer<typeof CatalogRecordStateSchema>;
