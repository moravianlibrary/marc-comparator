import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router";
import * as z from "zod";

type Primitive = string | number | boolean | null | undefined;

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
        const newKey = prefix ? `${prefix}.${key}` : key;
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
        const parts = key.split(".");
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

export function useSearchParamsState<Schema extends z.ZodTypeAny>(
    schema: Schema
) {
    const [searchParams, setSearchParams] = useSearchParams();

    const parseParams = useCallback((): z.infer<Schema> => {
        const flat: Record<string, string> = {};
        searchParams.forEach((value, key) => {
            flat[key] = value;
        });

        const obj = unflattenObject(flat);

        const parsed = schema.safeParse(obj);
        if (!parsed.success) {
            throw new Error("Invalid search params: " + parsed.error.message);
        }

        return parsed.data;
    }, [searchParams, schema]);

    const [state, setState] = useState<z.infer<Schema>>(parseParams);

    // Sync URL → state on navigation
    useEffect(() => {
        setState(parseParams());
    }, [searchParams, parseParams]);

    const update = useCallback(
        (nextPartial: Partial<z.infer<Schema>>) => {
            const parsed = schema.safeParse(nextPartial);
            if (!parsed.success) {
                throw new Error(
                    "Invalid update to search params: " + parsed.error.message
                );
            }

            const flat = flattenObject(parsed.data);
            const newParams = new URLSearchParams();
            for (const key in flat) {
                const value = flat[key];
                if (value !== undefined) {
                    const encoded = encodeValue(value);
                    if (encoded !== "") newParams.set(key, encoded);
                }
            }

            setSearchParams(newParams);
            setState(parsed.data);
        },
        [schema, setSearchParams]
    );

    return [state, update] as const;
}
