import { faker } from "@faker-js/faker";
import type { CatalogRecordState } from "../../models/primitives/catalog_record";

export const fakeCatalogRecordState = (): CatalogRecordState[] => {
    let state: CatalogRecordState[] = [];

    state.push(faker.datatype.boolean(0.95) ? "Active" : "Deleted");
    state.push(faker.datatype.boolean(0.5) ? "Unprocessed" : "Processed");
    state.push(faker.datatype.boolean(0.9) ? "Visible" : "Hidden");

    return state;
};
