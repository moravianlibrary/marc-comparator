import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router";
import * as z from "zod";

type Primitive = string | number | boolean | null | undefined;

const DOT_REPLACEMENT = "_d_";

function coerceValue(value: string): Primitive {
    if (value === "true") return true;
    if (value === "false") return false;
    if (!isNaN(Number(value))) return Number(value);
    return value;
}

// Convert value to string for URL
function encodeValue(value: Primitive): string {
    if (value === null || value === undefined) return "";
    return String(value);
}

// Flatten nested object to key.path = value
function flattenObject(obj: any, prefix = ""): Record<string, Primitive> {
    const result: Record<string, Primitive> = {};
    for (const key in obj) {
        const val = obj[key];
        const safeKey = key.replace(/\./g, DOT_REPLACEMENT);
        const newKey = prefix ? `${prefix}.${safeKey}` : safeKey;

        if (val !== null && typeof val === "object" && !Array.isArray(val)) {
            Object.assign(result, flattenObject(val, newKey));
        } else {
            result[newKey] = val;
        }
    }
    return result;
}

// Unflatten object from key.path notation
function unflattenObject(obj: Record<string, string>): Record<string, any> {
    const result: Record<string, any> = {};
    for (const key in obj) {
        const parts = key
            .split(".")
            .map((p) => p.replace(new RegExp(DOT_REPLACEMENT, "g"), "."));
        let current = result;
        for (let i = 0; i < parts.length; i++) {
            const part = parts[i];
            if (i === parts.length - 1) {
                current[part] = coerceValue(obj[key]);
            } else {
                current[part] = current[part] || {};
                current = current[part];
            }
        }
    }
    return result;
}

function deepMerge<T extends Record<string, any>>(a: T, b: T): T {
    const result: Record<string, any> = { ...a };

    for (const key in b) {
        if (
            b[key] &&
            typeof b[key] === "object" &&
            !Array.isArray(b[key]) &&
            a[key] &&
            typeof a[key] === "object" &&
            !Array.isArray(a[key])
        ) {
            result[key] = deepMerge(a[key], b[key]);
        } else {
            result[key] = b[key];
        }
    }

    return result as T;
}

function stateToUrl(parsedData: any, schema: z.ZodTypeAny): URLSearchParams {
    const flatMerged = flattenObject(parsedData);
    const newParams = new URLSearchParams();

    for (const key in flatMerged) {
        const pathParts = key.split(".");
        let currentSchema: any = schema;
        let metaUrl = false;

        for (const part of pathParts) {
            if (!currentSchema) break;
            if (currentSchema?.meta()?.url) metaUrl = true;

            if (currentSchema instanceof z.ZodObject)
                currentSchema = currentSchema.shape[part];
            else if (currentSchema instanceof z.ZodArray)
                currentSchema = currentSchema.element;
            else if (currentSchema instanceof z.ZodRecord)
                currentSchema = currentSchema.valueType;
            else currentSchema = undefined;
        }

        if (currentSchema?.meta()?.url) metaUrl = true;

        if (metaUrl) {
            const value = flatMerged[key];
            if (value !== undefined) {
                const encoded = encodeValue(value);
                if (encoded !== "") newParams.set(key, encoded);
            }
        }
    }

    return newParams;
}

export function useSearchParamsState<
    Schema extends z.ZodTypeAny,
    Action = unknown
>(
    schema: Schema,
    options?: {
        storeKey?: string;
        defaultValues?: Partial<z.infer<Schema>>;
        softDefaultValues?: Partial<z.infer<Schema>>;
        reducer?: (state: z.infer<Schema>, action: Action) => z.infer<Schema>;
    }
) {
    const [searchParams, setSearchParams] = useSearchParams();

    // Load stored data (if any)
    const loadStored = useCallback((): z.infer<Schema> | null => {
        if (!options?.storeKey) return null;

        const raw = localStorage.getItem(options.storeKey);
        if (!raw) return null;

        const parsedObj = JSON.parse(raw);
        const parsed = schema.safeParse(parsedObj);

        return parsed.success ? parsed.data : null;
    }, [options?.storeKey, schema]);

    const initialState = useMemo(() => {
        const flat: Record<string, string> = {};
        searchParams.forEach((value, key) => (flat[key] = value));

        const fromUrl = unflattenObject(flat);

        if (Object.keys(fromUrl).length > 0) {
            const parsed = schema.safeParse(
                deepMerge(options?.defaultValues || {}, fromUrl)
            );

            if (!parsed.success) {
                throw new Error(
                    "Invalid search params: " + parsed.error.message
                );
            }

            if (options?.storeKey) {
                localStorage.setItem(
                    options.storeKey,
                    JSON.stringify(parsed.data)
                );
            }

            return parsed.data;
        }

        const fromStore = loadStored();

        const parsed = schema.safeParse(
            deepMerge(
                options?.defaultValues || {},
                fromStore || options?.softDefaultValues || {}
            )
        );

        if (!parsed.success) {
            throw new Error("Invalid search params: " + parsed.error.message);
        }

        return parsed.data;
    }, [searchParams, schema, loadStored, options?.defaultValues]);

    useEffect(() => {
        setSearchParams(stateToUrl(initialState, schema));
    }, []);

    const [state, setState] = useState<z.infer<Schema>>(initialState);

    const update = useCallback(
        (nextPartial: Partial<z.infer<Schema>>) => {
            const parsed = schema.safeParse(nextPartial);
            if (!parsed.success) {
                throw new Error(
                    "Invalid update to search params: " + parsed.error.message
                );
            }

            setSearchParams(stateToUrl(parsed.data, schema));
            setState(parsed.data);

            if (options?.storeKey) {
                localStorage.setItem(
                    options.storeKey,
                    JSON.stringify(parsed.data)
                );
            }
        },
        [schema, setSearchParams, options?.storeKey]
    );

    const dispatch = useCallback(
        (action: Action) => {
            if (!options?.reducer) {
                throw new Error("Reducer not provided, cannot dispatch");
            }

            const next = options.reducer(state, action);

            update(next);
        },
        [state, update, options?.reducer]
    );

    return { state, update, dispatch } as const;
}
