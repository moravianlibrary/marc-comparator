export interface SearchConfig {
    fields: string[];
    fuzziness?: Record<string, string>;
    defaultFuzziness?: string;
    phraseBoosts?: Record<string, number>;
    prefixBoosts?: Record<string, number>;
    fuzzyBoosts?: Record<string, number>;
}

export interface PerPageConfig {
    options: number[];
    default: number;
}
