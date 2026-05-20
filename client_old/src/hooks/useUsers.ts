import { useMutation, useQuery } from "@tanstack/react-query";
import apiClient from "../services/apiClient";
import type { RoleResponse } from "../models/api/responses/roles";
import type { UserId, UsersPage } from "../models/api/responses/users";
import { queryClient } from "../services/queryClient";

// -------------------------
// Queries
// -------------------------
export const useGetUsers = (
    params?: { page: number; page_size: number; email: string | null },
    enabled = true
) =>
    useQuery<UsersPage>({
        queryKey: ["users", params],
        queryFn: async () =>
            (
                await apiClient.get<UsersPage>(`/access-control/users`, {
                    params,
                })
            ).data,
        enabled,
    });

// -------------------------
// Mutations
// -------------------------
export const useAssignUserRole = () =>
    useMutation<RoleResponse, Error, { user_id: UserId; role_id: number }>({
        mutationFn: async ({ user_id, role_id }) =>
            (
                await apiClient.patch<RoleResponse>(
                    `/access-control/users/${user_id}/assign-role/${role_id}`
                )
            ).data,
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["users"],
                exact: true,
            });
            // TODO: Display success notification
        },
    });

export const useUnassignUserRole = () =>
    useMutation<RoleResponse, Error, { user_id: UserId; role_id: number }>({
        mutationFn: async ({ user_id, role_id }) =>
            (
                await apiClient.patch<RoleResponse>(
                    `/access-control/users/${user_id}/unassign-role/${role_id}`
                )
            ).data,
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["users"],
                exact: true,
            });
            // TODO: Display success notification
        },
    });
