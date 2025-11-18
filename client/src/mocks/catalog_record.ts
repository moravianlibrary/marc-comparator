import { Factory, Response, Server } from "miragejs";
import { faker } from "@faker-js/faker";
import type { CatalogRecord } from "../models/api/responses/catalog_record";
import { fakeCatalogBase, fakeSystemNumber } from "./fake/identifiers";
import { fakeValidationResults } from "./fake/validation";
import { fakeCatalogRecordState } from "./fake/catalog_record";
import { buildSearchResponse } from "./es_factories";
import { fakeComparisonResults } from "./fake/comparison";
import type { MarcRecord } from "../models/api/responses/marc_record";
import { fakeVariableFields } from "./fake/marc_record";
import { fakeAuthorityLinks } from "./fake/authority_link";
import { type Task } from "../models/api/responses/task";

export const catalogRecordFactory = Factory.extend<CatalogRecord>({
    base: () => fakeCatalogBase(),
    system_number: () => fakeSystemNumber(),

    type_of_record: () => faker.helpers.arrayElement(["bib", "auth", "hold"]),
    bibliographic_level: () =>
        faker.helpers.arrayElement(["m", "s", "c", "a", "b", "i", "v"]),

    title: () => faker.lorem.words(faker.number.int({ min: 1, max: 10 })),
    subtitle: () =>
        faker.datatype.boolean()
            ? faker.lorem.words(faker.number.int({ min: 2, max: 20 }))
            : undefined,
    authors: () =>
        faker.datatype.boolean()
            ? [faker.person.lastName() + ", " + faker.person.firstName()]
            : [],

    latest_sync: () => faker.date.recent(),

    state: () => fakeCatalogRecordState(),

    authority_links: () => fakeAuthorityLinks(),
    comparisons: () => fakeComparisonResults(),
    validations: () => fakeValidationResults(),
});

export function catalogRecordSeeds(server: Server) {
    server.createList("catalog-record", 72);
}

export const marcRecordFactory = Factory.extend<MarcRecord>({
    leader: () => "00000nam a2200000 a 4500",
    fixed_fields: () => ({
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
    }),
    variable_fields: () => fakeVariableFields(),
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

            const marc = {
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
            };

            return new Response(200, {}, marc);
        }
    );

    this.post("/records/fetch", (schema: any, request: any) => {
        const attrs = JSON.parse(request.requestBody);
        const { base, systemNumber } = attrs;

        const task: Task = {
            task_id: faker.string.uuid(),
            name: `Fetch record ${base}-${systemNumber}`,
            type: "FetchRecord",
            status: "Pending",
            outcome_severity: "Info",
            created_by: faker.string.uuid(),
            created_at: new Date(),
            started_at: null,
            finished_at: null,
        };
        return new Response(200, {}, task);
    });

    this.post("/records/fetch-batch", (schema: any, request: any) => {
        const task: Task = {
            task_id: faker.string.uuid(),
            name: `Fetch batch of records`,
            type: "FetchBatchOfRecords",
            status: "Pending",
            outcome_severity: "Info",
            created_by: faker.string.uuid(),
            created_at: new Date(),
            started_at: null,
            finished_at: null,
        };
        return new Response(200, {}, task);
    });

    this.post("/records/sync", (schema: any, request: any) => {
        const task: Task = {
            task_id: faker.string.uuid(),
            name: `Sync catalog records from catalog`,
            type: "SyncRecords",
            status: "Pending",
            outcome_severity: "Info",
            created_by: faker.string.uuid(),
            created_at: new Date(),
            started_at: null,
            finished_at: null,
        };
        return new Response(200, {}, task);
    });
}
