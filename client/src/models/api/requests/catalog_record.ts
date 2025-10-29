import { z } from "zod";

export const HideCatalogRecordsParamsSchema = z.object({
    reason: z.string().optional(),
});
export type HideCatalogRecordsParams = z.infer<
    typeof HideCatalogRecordsParamsSchema
>;
