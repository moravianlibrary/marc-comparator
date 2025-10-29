import { z } from "zod";

export const ValidityStatusSchema = z.enum([
    "Valid",
    "Invalid",
    "Warning",
    "Info",
]);
export type ValidityStatus = z.infer<typeof ValidityStatusSchema>;
