import { faker } from "@faker-js/faker";
import type { CatalogRecordState } from "../../models/primitives/catalog_record";

export const fakeCatalogRecordState = (): CatalogRecordState[] => {
    let state: CatalogRecordState[] = [];

    state.push(faker.datatype.boolean(0.95) ? "Active" : "Deleted");

    if (faker.datatype.boolean(0.1)) {
        state.push("Hidden");
    }

    state.push(faker.datatype.boolean(0.8) ? "Valid" : "Invalid");

    return state;
};
