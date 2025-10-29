import { Factory, Response, Server } from "miragejs";
import { faker } from "@faker-js/faker";
import type { CatalogRecord } from "../models/api/responses/catalog_record";
import { fakeCatalogBase, fakeSystemNumber } from "./fake/identifiers";
import { fakeValidationResults } from "./fake/validation";
import { fakeCatalogRecordState } from "./fake/catalog_record";
import { buildSearchResponse } from "./es_factories";
import {
    fakeAuthorityRecordIds,
    fakeComparisonResults,
} from "./fake/comparison";
import type { MarcRecord } from "../models/api/responses/marc_record";
import { fakeVariableFields } from "./fake/marc_record";

export const catalogRecordFactory = Factory.extend<CatalogRecord>({
    base: () => fakeCatalogBase(),
    system_number: () => fakeSystemNumber(),

    last_sync: () => faker.date.recent(),

    state: () => fakeCatalogRecordState(),

    validation_results: () => fakeValidationResults(),
    authority_record_ids: () => fakeAuthorityRecordIds(),
    comparison_results: () => fakeComparisonResults(),
});

export function catalogRecordSeeds(server: Server) {
    server.createList("catalog-record", 72);
}

export const marcRecordFactory = Factory.extend<MarcRecord>({
    leader: "00000nam a2200000 a 4500",
    fixed_fields: {
        "001": faker.string.uuid(),
        "005": new Date().toISOString(),
        "008": `${faker.date
            .past({ years: 1 })
            .toISOString()
            .slice(2, 10)
            .replace(/-/g, "")}s${faker.number.int({
            min: 1980,
            max: 2025,
        })}    xxu           000 0 eng d`,
    },
    variable_fields: fakeVariableFields(),
});

export function catalogRecordRoutes(this: any) {
    this.post("/records/search", (schema: any, request: any) =>
        buildSearchResponse(
            schema,
            request,
            "catalog-record",
            (model: Partial<CatalogRecord>) =>
                `${model.base}-${model.system_number}`
        )
    );

    this.get(
        "/records/marc/:base/:system_number",
        (schema: any, request: any) => {
            if (faker.number.float({ min: 0, max: 1 }) < 0.1) {
                return new Response(
                    404,
                    {},
                    { error: "Catalog record not found" }
                );
            }

            return schema.create("marc-record").attrs;
        }
    );
}
