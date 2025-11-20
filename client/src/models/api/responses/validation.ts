import { z } from "zod";
import { ValidityStatusSchema } from "../../primitives/validation";

export const ValidationTargetSchema = z.object({
    tag: z.string().regex(/^\d{3}$/),
    codes: z.array(z.string()).optional(),
    idx: z.number().optional(),
});
export type ValidationTarget = z.infer<typeof ValidationTargetSchema>;

export const ValidationSchema = z.object({
    validator: z.string(),
    target: ValidationTargetSchema,
    status: ValidityStatusSchema,
    reason: z.string().optional(),
    details: z.string().optional(),
    hints: z.string().optional(),
    updated_at: z.date(),
});
export type Validation = z.infer<typeof ValidationSchema>;
