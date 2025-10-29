import { faker } from "@faker-js/faker";
import type { VariableField } from "../../models/api/responses/marc_record";

// Helper for random subfields
export const fakeSubfields = (): Record<string, string[]> => {
    const count = faker.number.int({ min: 1, max: 4 });
    const subs: Record<string, string[]> = {};
    for (let i = 0; i < count; i++) {
        const code = faker.string.alpha({ length: 1, casing: "lower" });
        subs[code] = [faker.lorem.words(faker.number.int({ min: 1, max: 4 }))];
    }
    return subs;
};

export const fakeVariableField = (): VariableField => ({
    ind1: faker.helpers.arrayElement([" ", "0", "1", "2"]),
    ind2: faker.helpers.arrayElement([" ", "0", "1", "2"]),
    subfields: fakeSubfields(),
});

// Common MARC fields
export const fakeVariableFields = () => {
    const year = faker.date.past({ years: 30 }).getFullYear().toString();
    const author = `${faker.person.lastName()}, ${faker.person.firstName()}`;
    const title = faker.lorem.sentence({ min: 3, max: 6 });

    return {
        // ISBN
        "020": [
            {
                ind1: " ",
                ind2: " ",
                subfields: {
                    a: [
                        faker.number
                            .int({ min: 1000000000000, max: 9999999999999 })
                            .toString(),
                    ],
                },
            },
        ],

        // Language
        "041": [
            {
                ind1: "0",
                ind2: " ",
                subfields: {
                    a: [
                        faker.helpers.arrayElement([
                            "eng",
                            "fre",
                            "ger",
                            "spa",
                            "ita",
                            "slk",
                        ]),
                    ],
                },
            },
        ],

        // Main Entry – Personal Name
        "100": [
            {
                ind1: "1",
                ind2: " ",
                subfields: { a: [author] },
            },
        ],

        // Title and Statement of Responsibility
        "245": [
            {
                ind1: "1",
                ind2: "0",
                subfields: {
                    a: [title],
                    b: [faker.lorem.words(3)],
                    c: [author],
                },
            },
        ],

        // Edition Statement
        "250": [
            {
                ind1: " ",
                ind2: " ",
                subfields: {
                    a: [`${faker.number.int({ min: 1, max: 5 })}th edition`],
                },
            },
        ],

        // Publication Info
        "264": [
            {
                ind1: " ",
                ind2: "1",
                subfields: {
                    a: [faker.location.city()],
                    b: [faker.company.name()],
                    c: [year],
                },
            },
        ],

        // Physical Description
        "300": [
            {
                ind1: " ",
                ind2: " ",
                subfields: {
                    a: [`${faker.number.int({ min: 50, max: 500 })} pages`],
                    b: [
                        `${faker.helpers.arrayElement([
                            "illustrations",
                            "maps",
                            "charts",
                        ])}`,
                    ],
                    c: ["24 cm"],
                },
            },
        ],

        // Series
        "490": [
            {
                ind1: "1",
                ind2: " ",
                subfields: {
                    a: [
                        `${faker.lorem.words(2)} series ; v.${faker.number.int({
                            min: 1,
                            max: 5,
                        })}`,
                    ],
                },
            },
        ],

        // Subject Headings
        "650": Array.from(
            { length: faker.number.int({ min: 2, max: 4 }) },
            () => ({
                ind1: " ",
                ind2: "0",
                subfields: {
                    a: [
                        faker.helpers.arrayElement([
                            "Artificial intelligence",
                            "Data science",
                            "Libraries",
                            "History",
                            "Programming",
                        ]),
                    ],
                    x: [
                        faker.helpers.arrayElement([
                            "Study and teaching",
                            "Case studies",
                            "History",
                            "Automation",
                        ]),
                    ],
                },
            })
        ),

        // General Note
        "500": [
            {
                ind1: " ",
                ind2: " ",
                subfields: { a: [faker.lorem.sentence()] },
            },
        ],

        // Added Entry – Personal Name
        "700": [
            {
                ind1: "1",
                ind2: " ",
                subfields: {
                    a: [
                        `${faker.person.lastName()}, ${faker.person.firstName()}`,
                    ],
                },
            },
        ],

        // Random “wildcards”
        "856": [
            {
                ind1: "4",
                ind2: "0",
                subfields: {
                    u: [
                        `https://${faker.internet.domainName()}/${faker.word.sample()}`,
                    ],
                    y: ["Full text online"],
                },
            },
        ],
    };
};
