import { faker } from "@faker-js/faker";
import {
    fakeCatalogBase,
    fakeSubfieldCode,
    fakeSystemNumber,
    fakeTag,
} from "./identifiers";
import type {
    Comparison,
    FieldComparisonResult,
    SubfieldComparisonResult,
} from "../../models/api/responses/comparison";

export const fakeSubfieldComparisonResult = (): SubfieldComparisonResult => {
    return {
        code: fakeSubfieldCode(),
        score: faker.number.float({ min: 0, max: 100, fractionDigits: 2 }),
        explanation: faker.datatype.boolean()
            ? faker.lorem.sentence()
            : undefined,
        details: faker.datatype.boolean()
            ? faker.lorem.paragraphs(2)
            : undefined,
    };
};

export const fakeFieldComparisonResult = (): FieldComparisonResult => {
    return {
        tag: fakeTag(),
        score: faker.number.float({ min: 0, max: 100, fractionDigits: 2 }),
        explanation: faker.datatype.boolean()
            ? faker.lorem.sentence()
            : undefined,
        details: faker.datatype.boolean()
            ? faker.lorem.paragraphs(2)
            : undefined,
        subfield_results: faker.datatype.boolean()
            ? Array.from(
                  {
                      length: faker.number.int({ min: 1, max: 5 }),
                  },
                  fakeSubfieldComparisonResult
              )
            : undefined,
    };
};

export const fakeComparisonResult = (): Comparison => {
    return {
        comparator: faker.lorem.word(),
        base: fakeCatalogBase(),
        system_number: fakeSystemNumber(),
        overall_score: faker.number.float({
            min: 0,
            max: 100,
            fractionDigits: 2,
        }),
        summary: faker.lorem.sentence(),
        field_results: Array.from(
            { length: faker.number.int({ min: 1, max: 10 }) },
            fakeFieldComparisonResult
        ),
        updated_at: faker.date.recent(),
    };
};

export const fakeComparisonResults = (): Comparison[] => {
    return Array.from(
        { length: faker.number.int({ min: 1, max: 7 }) },
        fakeComparisonResult
    );
};
