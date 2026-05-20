import { z } from "zod";
import { EsQuerySchema } from "./es_query";

export const AddOneRecordDataSchema = z.object({
    base: z.string(),
    system_number: z.string(),
});
export type AddOneRecordData = z.infer<typeof AddOneRecordDataSchema>;

export const AddBatchOfRecordsDataSchema = z.object({
    per_base: z.object({
        base: z.string(),
        system_numbers: z.array(z.string()),
    }),
});
export type AddBatchOfRecordsData = z.infer<typeof AddBatchOfRecordsDataSchema>;

export const SyncRecordsDataSchema = z.object({
    base: z.string(),
    from_date: z.date().optional(),
});
export type SyncRecordsData = z.infer<typeof SyncRecordsDataSchema>;

export const SetRecordsVisibilityDataSchema = z.object({
    query: EsQuerySchema,
    visible: z.boolean(),
});
export type SetRecordsVisibilityData = z.infer<
    typeof SetRecordsVisibilityDataSchema
>;
