import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "../services/apiClient";
import type {
    SettingsDomain,
    SettingsScope,
} from "../models/primitives/settings";
import type {
    Settings,
    SettingsJsonSchema,
} from "../models/api/responses/settings";

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

export const useGetSettings = (
    domain: SettingsDomain,
    scope: SettingsScope,
    enabled = true
) =>
    useQuery<Settings>({
        queryKey: ["settings", domain, scope],
        queryFn: async () =>
            (await apiClient.get<Settings>(`/settings/${domain}/${scope}`))
                .data,
        enabled,
    });

// -------------------------
// Mutations
// -------------------------
export const useSetSettings = (
    domain: SettingsDomain,
    scope: SettingsScope,
    settings: Settings
) =>
    useMutation<Settings, Error, void>({
        mutationFn: async () =>
            (
                await apiClient.post<Settings>(
                    `/settings/${domain}/${scope}`,
                    settings
                )
            ).data,
        onSuccess: () => {
            useQueryClient().invalidateQueries({
                queryKey: ["settings", domain, scope],
                exact: true,
            });
        },
    });
