import { faker } from "@faker-js/faker";

export const fakeSystemNumber = (): string => {
    return faker.string.numeric(9);
};

export const fakeCatalogBase = (): string => {
    return faker.helpers.arrayElement(["MZK01", "MZK03", "SKC", "KNAV"]);
};

export const fakeCatalogRecordId = (): string => {
    return `${fakeCatalogBase()}-${fakeSystemNumber()}`;
};

export const fakeTag = (): string => {
    return faker.string.numeric({ length: 3 });
};

export const fakeSubfieldCode = (): string => {
    return faker.string.alphanumeric({ length: 1 });
};

export const fakeSubfieldCodes = (): string[] => {
    return Array.from(
        { length: faker.number.int({ min: 0, max: 3 }) },
        fakeSubfieldCode
    );
};

export const fakeIsbn13 = (): string => {
    const parts = [3, 1, 2, 6, 1].map((len) => faker.string.numeric(len));
    return parts.join("-");
};

export const fakeIssn8 = (): string => {
    return `${faker.string.numeric(4)}-${faker.string.numeric(4)}`;
};

export const fakeIsxn = (): string => {
    return faker.helpers.arrayElement([fakeIsbn13(), fakeIssn8()]);
};

export const fakeNbn = (): string => {
    return `cnb${faker.string.numeric(9)}`;
};

export const fakeBarcode = (): string => {
    return faker.string.numeric(8);
};

export const fakeBarcodes = (): string[] => {
    return Array.from({ length: faker.number.int({ min: 1, max: 7 }) }, () =>
        fakeBarcode()
    );
};

export const fakeSignature = (): string => {
    return `${faker.string.numeric(1)}-${faker.string.numeric(4)}.${faker.string
        .alphanumeric(2)
        .toUpperCase()}`;
};

export const fakeSignatures = (): string[] => {
    return Array.from({ length: faker.number.int({ min: 1, max: 3 }) }, () =>
        fakeSignature()
    );
};
