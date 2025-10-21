import { z } from "zod";

export const PairToAuthoritiesParamsSchema = z.object({
    authority_bases: z.array(z.string()),
});
export type PairToAuthoritiesParams = z.infer<
    typeof PairToAuthoritiesParamsSchema
>;
