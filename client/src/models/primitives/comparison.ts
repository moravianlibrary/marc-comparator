import { z } from "zod";

export const MatchQualitySchema = z.enum(["Excellent", "Moderate", "Poor"]);

export type MatchQuality = z.infer<typeof MatchQualitySchema>;
