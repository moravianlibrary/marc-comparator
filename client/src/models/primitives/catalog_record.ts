import { z } from "zod";

export const MaterialTypeSchema = z.enum([
    "Book",
    "ContinuingResource",
    "Graphic",
    "Map",
    "Music",
    "Other",
]);
export type MaterialType = z.infer<typeof MaterialTypeSchema>;

export const CatalogRecordStateSchema = z.enum([
    "Hidden",
    "Deleted",
    "Active",
    "Valid",
    "Invalid",
]);
export type CatalogRecordState = z.infer<typeof CatalogRecordStateSchema>;
