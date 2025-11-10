import { z } from "zod";
import { EsQuerySchema } from "./es_query";

export const AddOneRecordDataSchema = z.object({
    base: z.string(),
    systemNumber: z.string(),
});
export type AddOneRecordData = z.infer<typeof AddOneRecordDataSchema>;

export const AddBatchOfRecordsDataSchema = z.object({
    per_base: z.object({
        base: z.string(),
        systemNumbers: z.array(z.string()),
    }),
});
export type AddBatchOfRecordsData = z.infer<typeof AddBatchOfRecordsDataSchema>;

export const SyncRecordsDataSchema = z.object({
    base: z.string(),
    from_date: z.date().optional(),
});
export type SyncRecordsData = z.infer<typeof SyncRecordsDataSchema>;

export const SetHiddenStateDataSchema = z.object({
    hide: z.boolean(),
    query: EsQuerySchema,
});
export type SetHiddenStateData = z.infer<typeof SetHiddenStateDataSchema>;
