import { z } from "zod";
import { EsQuerySchema } from "./es_query";

export const ValidateRecordsDataSchema = z.object({
    validators: z
        .array(z.string())
        .min(1, "At least one validator must be selected"),
    query: EsQuerySchema,
});
export type ValidateRecordsData = z.infer<typeof ValidateRecordsDataSchema>;
