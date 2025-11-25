import { z } from "zod";

export const ComparisonResultSchema = z.enum([
    "Valid",
    "ReviewRequired",
    "Invalid",
]);

export type ComparisonResult = z.infer<typeof ComparisonResultSchema>;

export function mapScoreToResult(score: number): ComparisonResult {
    if (score >= 90) {
        return "Valid";
    } else if (score >= 70) {
        return "ReviewRequired";
    } else {
        return "Invalid";
    }
}
