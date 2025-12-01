import { useMutation, useQuery } from "@tanstack/react-query";
import apiClient from "../services/apiClient";
import type {
    SettingsDomain,
    SettingsScope,
} from "../models/primitives/settings";
import type {
    Settings,
    SettingsJsonSchema,
} from "../models/api/responses/settings";
import { useMemo } from "react";
import jsonSchemaToZod from "json-schema-to-zod";
import { z, ZodType } from "zod";
import type { FieldValues } from "react-hook-form";
import { queryClient } from "../services/queryClient";

// -------------------------
// Queries
// -------------------------
export const useGetSettingsSchema = (
    domain: SettingsDomain,
    scope: SettingsScope,
    enabled = true
) =>
    useQuery<SettingsJsonSchema>({
        queryKey: ["settings", "schema", domain, scope],
        queryFn: async () =>
            await fetch(`/schemas/settings/${domain}/${scope}.json`).then(
                async (res) => res.json()
            ),
        enabled,
    });

function dereferenceJsonSchema(schema: any): any {
    const root = structuredClone(schema);
    const defs = root.$defs ?? {};

    function resolve(node: any): any {
        if (Array.isArray(node)) {
            return node.map(resolve);
        }

        if (node && typeof node === "object") {
            if (node.$ref && node.$ref.startsWith("#/$defs/")) {
                const name = node.$ref.replace("#/$defs/", "");
                if (!defs[name]) {
                    throw new Error(`Missing schema definition for ${name}`);
                }
                return resolve(structuredClone(defs[name]));
            }

            const out: any = {};
            for (const [k, v] of Object.entries(node)) {
                out[k] = resolve(v);
            }
            return out;
        }

        return node;
    }

    const deref = resolve(root);
    delete deref.$defs;

    return deref;
}

export function useGetSettingsZodSchema(
    domain: SettingsDomain,
    scope: SettingsScope,
    enabled = true
) {
    const query = useGetSettingsSchema(domain, scope, enabled);

    const zodSchema = useMemo(() => {
        if (!query.data) return undefined;
        try {
            const dereferenced = dereferenceJsonSchema(query.data);
            const code = jsonSchemaToZod(dereferenced);

            const factory = new Function("z", `return (${code});`);

            return factory(z) as ZodType<FieldValues>;
        } catch (err) {
            console.error("Schema transformation failed", err);
            return undefined;
        }
    }, [query.data]);

    return {
        ...query,
        zodSchema,
    };
}

export const useGetSettings = (
    domain: SettingsDomain,
    scope: SettingsScope,
    enabled = true
) =>
    useQuery<Settings>({
        queryKey: ["settings", domain, scope],
        queryFn: async () =>
            apiClient
                .get<Settings>(`/settings/${domain}/${scope}`)
                .then((res) => res.data)
                .catch((err) => {
                    if (err.status === 404) {
                        console.warn(
                            "Settings not found, returning empty object"
                        );
                        return {};
                    }
                    throw err;
                }),
        enabled,
    });

// -------------------------
// Mutations
// -------------------------
export const useSetSettings = (domain: SettingsDomain, scope: SettingsScope) =>
    useMutation<Settings, Error, Settings>({
        mutationFn: async (settings: Settings) =>
            (
                await apiClient.post<Settings>(
                    `/settings/${domain}/${scope}`,
                    settings
                )
            ).data,
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["settings", domain, scope],
                exact: true,
            });
        },
    });
