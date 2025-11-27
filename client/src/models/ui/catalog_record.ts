import type { CatalogRecordState } from "../primitives/catalog_record";

const STATE_RANKING: Record<CatalogRecordState, number> = {
    Active: 1,
    Deleted: 2,
    Hidden: 3,
    Visible: 4,
};

export function stateOrder(
    a: CatalogRecordState,
    b: CatalogRecordState
): number {
    return STATE_RANKING[a] - STATE_RANKING[b];
}

const STATE_COLOR_MAP: Record<CatalogRecordState, "teal" | "grey" | "blue"> = {
    Active: "teal",
    Deleted: "grey",
    Hidden: "blue",
    Visible: "blue",
};

export function stateColor(
    state: CatalogRecordState
): "teal" | "grey" | "blue" {
    return STATE_COLOR_MAP[state];
}
