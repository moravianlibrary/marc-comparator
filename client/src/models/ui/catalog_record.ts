import type { CatalogRecordState } from "../primitives/catalog_record";

const STATE_RANKING: Record<CatalogRecordState, number> = {
    Active: 1,
    Deleted: 2,
    Valid: 3,
    Invalid: 4,
    Hidden: 5,
};

export function stateOrder(
    a: CatalogRecordState,
    b: CatalogRecordState
): number {
    return STATE_RANKING[a] - STATE_RANKING[b];
}

const STATE_COLOR_MAP: Record<
    CatalogRecordState,
    "teal" | "grey" | "green" | "red" | "blue"
> = {
    Active: "teal",
    Deleted: "grey",
    Valid: "green",
    Invalid: "red",
    Hidden: "blue",
};

export function stateColor(
    state: CatalogRecordState
): "teal" | "grey" | "green" | "red" | "blue" {
    return STATE_COLOR_MAP[state];
}
