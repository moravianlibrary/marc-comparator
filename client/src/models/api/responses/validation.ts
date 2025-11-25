import { z } from "zod";
import { ValidityStatusSchema } from "../../primitives/validation";

export const ValidationTargetSchema = z.object({
    tag: z.string().regex(/^\d{3}$/),
    codes: z.array(z.string()).optional().nullable(),
    idx: z.number().optional().nullable(),
});
export type ValidationTarget = z.infer<typeof ValidationTargetSchema>;

export const ValidationSchema = z.object({
    validator: z.string(),
    target: ValidationTargetSchema,
    status: ValidityStatusSchema,
    reason: z.string().optional().nullable(),
    details: z.string().optional().nullable(),
    hint: z.string().optional().nullable(),
    updated_at: z.coerce.date(),
});
export type Validation = z.infer<typeof ValidationSchema>;
