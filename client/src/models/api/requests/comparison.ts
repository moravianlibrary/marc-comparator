import { z } from "zod";
import { EsQuerySchema } from "./es_query";

export const CompareRecordsDataSchema = z.object({
    target_base: z.string(),
    comparator: z.string(),
    query: EsQuerySchema,
});
export type CompareRecordsData = z.infer<typeof CompareRecordsDataSchema>;
