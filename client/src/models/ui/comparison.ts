import {
    mapScoreToResult,
    type ComparisonResult,
} from "../primitives/comparison";

const RESULT_COLOR_MAP: Record<ComparisonResult, "green" | "yellow" | "red"> = {
    Valid: "green",
    ReviewRequired: "yellow",
    Invalid: "red",
};

export function resultColor(
    result: ComparisonResult
): "green" | "yellow" | "red" {
    return RESULT_COLOR_MAP[result];
}

export function scoreColor(score: number): "green" | "yellow" | "red" {
    return resultColor(mapScoreToResult(score));
}
