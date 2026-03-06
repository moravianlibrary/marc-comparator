import { z } from "zod";

export const CatalogRecordStateSchema = z.enum([
    "Active",
    "Deleted",
    "Unprocessed",
    "Processed",
    "Visible",
    "Hidden",
]);
export type CatalogRecordState = z.infer<typeof CatalogRecordStateSchema>;

const STATE_RANKING: Record<CatalogRecordState, number> = {
    Active: 1,
    Deleted: 2,
    Unprocessed: 3,
    Processed: 4,
    Hidden: 5,
    Visible: 6,
};

export const orderBy = (a: CatalogRecordState, b: CatalogRecordState) =>
    STATE_RANKING[a] - STATE_RANKING[b];
