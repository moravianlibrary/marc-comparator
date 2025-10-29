import { faker } from "@faker-js/faker";
import type { AuthorityRecordId } from "../../models/api/responses/catalog_record";
import {
    fakeCatalogBase,
    fakeSubfieldCodes,
    fakeSystemNumber,
    fakeTag,
} from "./identifiers";
import type {
    ComparisonResult,
    ComparisonTarget,
} from "../../models/api/responses/comparison";

export const fakeAuthorityRecordIds = (): AuthorityRecordId[] => {
    return Array.from({ length: faker.number.int({ min: 1, max: 2 }) }, () => {
        return {
            base: fakeCatalogBase(),
            system_number: fakeSystemNumber(),
        };
    });
};

export const fakeComparisonTarget = (): ComparisonTarget => {
    return {
        tag: fakeTag(),
        codes: fakeSubfieldCodes(),
        score: faker.number.float({ min: 0, max: 100, fractionDigits: 2 }),
        reason: faker.datatype.boolean() ? faker.lorem.sentence() : undefined,
        details: faker.datatype.boolean()
            ? faker.lorem.paragraphs(2)
            : undefined,
    };
};

export const fakeComparisonResult = (): ComparisonResult => {
    return {
        base: fakeCatalogBase(),
        system_number: fakeSystemNumber(),
        overall_score: faker.number.float({
            min: 0,
            max: 100,
            fractionDigits: 2,
        }),
        summary: faker.lorem.sentence(),
        targets: Array.from(
            { length: faker.number.int({ min: 1, max: 5 }) },
            fakeComparisonTarget
        ),
    };
};

export const fakeComparisonResults = (): ComparisonResult[] => {
    return Array.from(
        { length: faker.number.int({ min: 1, max: 7 }) },
        fakeComparisonResult
    );
};
