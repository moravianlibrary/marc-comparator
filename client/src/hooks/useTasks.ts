import {
    useMutation,
    useQueries,
    useQuery,
    useQueryClient,
    type UseQueryResult,
} from "@tanstack/react-query";
import apiClient from "../services/apiClient";
import { type EsQuery } from "../models/api/requests/es_query";
import {
    SearchTasksResponseSchema,
    TaskSchema,
    type SearchTasksResponse,
    type Task,
} from "../models/api/responses/task";
import type { EsRequest } from "../models/api/requests/es";
import { useNotification } from "./useNotifications";

// -------------------------
// Queries
// -------------------------
export const useSearchTasks = (request: EsRequest, enabled = true) =>
    useQuery<SearchTasksResponse>({
        queryKey: ["tasks", "search", request],
        queryFn: async () =>
            SearchTasksResponseSchema.parse(
                (await apiClient.post("/tasks/search", request)).data
            ),
        enabled,
    });

export const useSearchTasksBatch = (
    requests: EsRequest[],
    enabled = true
): UseQueryResult<SearchTasksResponse>[] =>
    useQueries({
        queries: requests.map((request, idx) => ({
            queryKey: ["tasks", "search", idx, request],
            queryFn: async () =>
                SearchTasksResponseSchema.parse(
                    (await apiClient.post("/tasks/search", request)).data
                ),
            enabled,
        })),
    });

// -------------------------
// Mutations Templates
// -------------------------
export const useCreateTask = <T>(path: string) => {
    const { addTaskCreatedNotification } = useNotification();

    return useMutation<Task, Error, T>({
        mutationFn: async (data: T) =>
            TaskSchema.parse((await apiClient.post(path, data)).data),
        onSuccess: (taskData) => {
            // Notify
            addTaskCreatedNotification(taskData);
            // Invalidate
            useQueryClient().invalidateQueries({
                queryKey: ["tasks"],
                exact: true,
            });
        },
    });
};

// -------------------------
// Mutations
// -------------------------
export const useDeleteTasks = () =>
    useMutation<Task, Error, EsQuery>({
        mutationFn: async (query: EsQuery) =>
            (await apiClient.post<Task>(`/tasks/delete`, query)).data,
        onSuccess: () => {
            useQueryClient().invalidateQueries({
                queryKey: ["tasks"],
                exact: true,
            });
            // TODO: Show notification
        },
    });
