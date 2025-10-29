import { z } from "zod";
import { ValidityStatusSchema } from "../../primitives/validation";

export const ValidationTargetSchema = z.object({
    tag: z.string().regex(/^\d{3}$/),
    codes: z.array(z.string()).optional(),
});
export type ValidationTarget = z.infer<typeof ValidationTargetSchema>;

export const ValidationResultSchema = z.object({
    target: ValidationTargetSchema,
    status: ValidityStatusSchema,
    reason: z.string().optional(),
    details: z.string().optional(),
    hints: z.string().optional(),
});
export type ValidationResult = z.infer<typeof ValidationResultSchema>;
