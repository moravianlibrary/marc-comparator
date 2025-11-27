import { z } from "zod";

export const ValidityStatusSchema = z.enum([
    "Valid",
    "ForReview",
    "Invalid",
    "AdditionalInfo",
]);
export type ValidityStatus = z.infer<typeof ValidityStatusSchema>;
