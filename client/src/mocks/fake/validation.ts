import { faker } from "@faker-js/faker";
import type {
    ValidationResult,
    ValidationTarget,
} from "../../models/api/responses/validation";
import {
    ValidityStatusSchema,
    type ValidityStatus,
} from "../../models/primitives/validation";
import { fakeSubfieldCodes, fakeTag } from "./identifiers";

export const fakeValidationTarget = (): ValidationTarget => {
    return {
        tag: fakeTag(),
        codes: fakeSubfieldCodes(),
    };
};

export const fakeValidityStatus = (): ValidityStatus => {
    return faker.helpers.arrayElement(ValidityStatusSchema.options);
};

export const fakeValidationResult = (): ValidationResult => {
    return {
        target: fakeValidationTarget(),
        status: fakeValidityStatus(),
        reason: faker.datatype.boolean() ? faker.lorem.sentence() : undefined,
        details: faker.datatype.boolean() ? faker.lorem.paragraph() : undefined,
        hints: faker.datatype.boolean() ? faker.lorem.sentence() : undefined,
    };
};

export const fakeValidationResults = (): ValidationResult[] => {
    return Array.from({ length: faker.number.int({ min: 1, max: 5 }) }, () =>
        fakeValidationResult()
    );
};
