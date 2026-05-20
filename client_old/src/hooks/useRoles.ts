import { useMutation, useQuery } from "@tanstack/react-query";
import apiClient from "../services/apiClient";
import type { RoleResponse, RolesPage } from "../models/api/responses/roles";
import { type EditRole } from "../models/api/requests/roles";
import { queryClient } from "../services/queryClient";

// -------------------------
// Queries
// -------------------------
export const useGetRoles = (
    params?: { page: number; page_size: number },
    enabled = true
) =>
    useQuery<RolesPage>({
        queryKey: ["roles", params],
        queryFn: async () =>
            (
                await apiClient.get<RolesPage>(`/access-control/roles`, {
                    params,
                })
            ).data,
        enabled,
    });

// -------------------------
// Mutations
// -------------------------
export const useCreateRole = () =>
    useMutation<RoleResponse, Error, EditRole>({
        mutationFn: async (data: EditRole) =>
            (await apiClient.post<RoleResponse>(`/access-control/roles`, data))
                .data,
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["roles"],
                exact: true,
            });
            // TODO: Display success notification
        },
    });

export const useUpdateRole = () =>
    useMutation<RoleResponse, Error, { id: number; data: EditRole }>({
        mutationFn: async ({ id, data }) =>
            (
                await apiClient.put<RoleResponse>(
                    `/access-control/roles/${id}`,
                    data
                )
            ).data,
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["roles"],
                exact: true,
            });
            // TODO: Display success notification
        },
    });

export const useDeleteRole = () =>
    useMutation<RoleResponse, Error, { id: number }>({
        mutationFn: async ({ id }) =>
            (
                await apiClient.delete<RoleResponse>(
                    `/access-control/roles/${id}`
                )
            ).data,
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["roles"],
                exact: true,
            });
            // TODO: Display success notification
        },
    });
