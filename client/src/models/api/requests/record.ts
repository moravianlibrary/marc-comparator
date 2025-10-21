import { z } from "zod";

export const HideRecordsParamsSchema = z.object({
    reason: z.string().optional(),
});
export type HideRecordsParams = z.infer<typeof HideRecordsParamsSchema>;
