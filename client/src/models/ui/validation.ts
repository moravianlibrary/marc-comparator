import type { ValidityStatus } from "../primitives/validation";

const VALIDITY_COLOR_MAP: Record<
    ValidityStatus,
    "green" | "red" | "yellow" | "blue"
> = {
    Valid: "green",
    Invalid: "red",
    Warning: "yellow",
    Info: "blue",
};

export function validityColor(
    status: ValidityStatus
): "green" | "red" | "yellow" | "blue" {
    return VALIDITY_COLOR_MAP[status];
}
