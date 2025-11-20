import {
    mapScoreToResult,
    type ComparisonResult,
} from "../primitives/comparison";
import type { ValidityStatus } from "../primitives/validation";

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

export function scoreToValidity(score: number): ValidityStatus {
    if (score >= 0.9) {
        return "Valid";
    } else if (score >= 0.7) {
        return "Warning";
    } else {
        return "Invalid";
    }
}
