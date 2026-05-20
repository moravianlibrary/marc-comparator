import { z } from "zod";
import { EsQuerySchema } from "./es_query";

export const AuthorityLinkingDataSchema = z.object({
    target_base: z.string(),
    linkers: z.array(z.string()),
    query: EsQuerySchema,
});
export type AuthorityLinkingData = z.infer<typeof AuthorityLinkingDataSchema>;
