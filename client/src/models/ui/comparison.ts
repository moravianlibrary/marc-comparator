import { type MatchQuality } from "../primitives/comparison";

const MATCH_QUALITY_COLOR_MAP: Record<
    MatchQuality,
    "green" | "yellow" | "red"
> = {
    Excellent: "green",
    Moderate: "yellow",
    Poor: "red",
};

export function matchQualityColor(
    result: MatchQuality
): "green" | "yellow" | "red" {
    return MATCH_QUALITY_COLOR_MAP[result];
}

export function scoreToMatchQuality(score: number): MatchQuality {
    if (score >= 0.9) {
        return "Excellent";
    } else if (score >= 0.7) {
        return "Moderate";
    } else {
        return "Poor";
    }
}
