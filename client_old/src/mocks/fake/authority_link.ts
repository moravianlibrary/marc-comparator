import { faker } from "@faker-js/faker";
import { fakeCatalogBase, fakeSystemNumber } from "./identifiers";
import { type AuthorityLink } from "../../models/api/responses/authority_link";

export const fakeAuthorityLink = (): AuthorityLink => {
    return {
        linker: faker.lorem.word(),
        base: fakeCatalogBase(),
        system_number: fakeSystemNumber(),
        confidence: faker.datatype.boolean()
            ? faker.number.float({ min: 0, max: 100, fractionDigits: 2 })
            : null,
        updated_at: faker.date.recent(),
    };
};

export const fakeAuthorityLinks = (): AuthorityLink[] => {
    return Array.from(
        { length: faker.number.int({ min: 0, max: 3 }) },
        fakeAuthorityLink
    );
};
