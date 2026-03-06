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
    server.create("catalog-record", {
        id: "MZK01-000000001",
        base: "MZK01",
        system_number: "000000001",
        type_of_record: "bib",
        bibliographic_level: "m",
        title: "Special Test Record",
        authoers: "Test Author",
        latest_sync: new Date(),
        state: ["Active"],
        authority_links: [
            {
                linker: "TestLinker",
                base: "SKC",
                system_number: "000123456",
                confidence: 0.95,
                updated_at: new Date(),
            },
        ],
        comparisons: [
            {
                comparator: "TestComparator",
                base: "SKC",
                system_number: "000123456",
                overall_score: 0.9,
                match_quality: "Excellent",
                summary: "Very long text summary of the comparison result.",
                updated_at: new Date(),
                field_results: [
                    {
                        tag: "008",
                        score: 1.0,
                        explanation: "Fields match exactly.",
                    },
                    {
                        tag: "100",
                        score: 0.8,
                        explanation: "Minor differences found.",
                        details: "Subfield 'a' differs slightly.",
                        subfield_results: [
                            {
                                code: "a",
                                score: 0.8,
                                explanation: "Subfield has minor differences.",
                            },
                        ],
                    },
                    {
                        tag: "105",
                        score: 0.0,
                        explanation: "Field missing in target record.",
                    },
                    {
                        tag: "106",
                        score: 0.0,
                        explanation: "Subfield missing in target record.",
                        subfield_results: [
                            {
                                code: "b",
                                score: 0.0,
                                explanation:
                                    "Subfield 'b' is missing in target record.",
                            },
                        ],
                    },
                    {
                        tag: "650",
                        idxA: 1,
                        idxB: 0,
                        score: 0.5,
                        explanation: "Significant differences found.",
                        details: "Multiple subfields differ.",
                        subfield_results: [
                            {
                                code: "a",
                                idxA: 0,
                                idxB: 0,
                                score: 0.6,
                                explanation:
                                    "Subfield 'a' has significant differences.",
                            },
                            {
                                code: "a",
                                idxA: 1,
                                idxB: 1,
                                score: 0.4,
                                explanation: "Subfield 'a' differs greatly.",
                            },
                        ],
                    },
                    {
                        tag: "650",
                        idxA: 0,
                        idxB: 1,
                        score: 0.7,
                        explanation: "Some differences found.",
                        details: "Subfields differ in content.",
                        subfield_results: [
                            {
                                code: "a",
                                score: 0.7,
                                explanation:
                                    "Subfield 'a' has some differences.",
                            },
                        ],
                    },
                ],
            },
        ],
        validations: [
            {
                validator: "Robert",
                target: {
                    tag: "008",
                },
                status: "Valid",
                reason: "I said so",
                updated_at: faker.date.recent(),
            },
            {
                validator: "Robert",
                target: {
                    tag: "008",
                },
                status: "Valid",
                reason: "I said so",
                updated_at: faker.date.recent(),
            },
            {
                validator: "RRobert",
                target: {
                    tag: "008",
                },
                status: "Valid",
                reason: "I said so",
                updated_at: faker.date.recent(),
            },
            {
                validator: "Robert",
                target: {
                    tag: "008",
                },
                status: "Valid",
                reason: "I said so",
                updated_at: faker.date.recent(),
            },
        ],
    });
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
    this.post("/catalog-records/search", (schema: any, request: any) =>
        buildSearchResponse(
            schema,
            request,
            "catalog-record",
            (model: Partial<CatalogRecord>) =>
                `${model.base}-${model.system_number}`,
        ),
    );

    this.get(
        "/catalog-records/marc/:base/:system_number",
        (schema: any, request: any) => {
            if (faker.number.float({ min: 0, max: 1 }) < 0.1) {
                return new Response(
                    404,
                    {},
                    { error: "Catalog record not found" },
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
                variable_fields:
                    request.params.system_number === "000123456"
                        ? {
                              ...fakeVariableFields(),
                              "105": [
                                  {
                                      ind1: " ",
                                      ind2: " ",
                                      subfields: {
                                          a: [request.params.base],
                                      },
                                  },
                              ],
                              "106": [
                                  {
                                      ind1: " ",
                                      ind2: " ",
                                      subfields: {
                                          a: [request.params.base],
                                          b: ["Additional data"],
                                      },
                                  },
                              ],
                          }
                        : request.params.system_number === "000000001"
                          ? {
                                ...fakeVariableFields(),
                                "106": [
                                    {
                                        ind1: " ",
                                        ind2: " ",
                                        subfields: {
                                            a: [request.params.base, "Extra"],
                                            // missing 'b' subfield
                                        },
                                    },
                                ],
                            }
                          : fakeVariableFields(),
            };

            return new Response(200, {}, marc);
        },
    );

    this.post("/catalog-records/fetch", (schema: any, request: any) => {
        const attrs = JSON.parse(request.requestBody);
        const { base, systemNumber } = attrs;

        const task: Task = {
            task_id: faker.string.uuid(),
            name: `Fetch record ${base}-${systemNumber}`,
            type: "FetchRecord",
            status: "Pending",
            severity: "Info",
            created_by: faker.string.uuid(),
            created_at: new Date(),
            started_at: null,
            finished_at: null,
            traceback_lines: null,
        };
        return new Response(200, {}, task);
    });

    this.post("/catalog-records/fetch-batch", (schema: any, request: any) => {
        const task: Task = {
            task_id: faker.string.uuid(),
            name: `Fetch batch of records`,
            type: "FetchBatchOfRecords",
            status: "Pending",
            severity: "Info",
            created_by: faker.string.uuid(),
            created_at: new Date(),
            started_at: null,
            finished_at: null,
            traceback_lines: null,
        };
        return new Response(200, {}, task);
    });

    this.post("/catalog-records/sync", (schema: any, request: any) => {
        const task: Task = {
            task_id: faker.string.uuid(),
            name: `Sync catalog records from catalog`,
            type: "SyncRecords",
            status: "Pending",
            severity: "Info",
            created_by: faker.string.uuid(),
            created_at: new Date(),
            started_at: null,
            finished_at: null,
            traceback_lines: null,
        };
        return new Response(200, {}, task);
    });
}
