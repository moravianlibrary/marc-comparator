import { z } from "zod";

export const createPageSchema = <T extends z.ZodTypeAny>(itemSchema: T) =>
    z.object({
        items: z.array(itemSchema),
        num_found: z.number(),
    });
