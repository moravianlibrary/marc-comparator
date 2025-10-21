import { z } from "zod";

export const CompareToAuthoritiesParamsSchema = z.object({
    authority_bases: z.array(z.string()),
});
export type CompareToAuthoritiesParams = z.infer<
    typeof CompareToAuthoritiesParamsSchema
>;
