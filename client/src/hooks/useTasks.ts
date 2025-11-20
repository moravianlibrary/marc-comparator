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
    type TracebackLinesRequestParams,
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

export const useGetTraceback = (
    id: string,
    params: TracebackLinesRequestParams | null = null,
    enabled = true
) =>
    useQuery<string[]>({
        queryKey: ["tasks", "traceback", id, params],
        queryFn: async () =>
            (
                await apiClient.get<string[]>(`/tasks/${id}/traceback`, {
                    params,
                })
            ).data,
        enabled,
    });

export const useDownloadTraceback = (
    id: string,
    params: TracebackLinesRequestParams | null = null,
    enabled = true
) => {
    const query = useGetTraceback(id, params, enabled);

    const download = async () => {
        const data = await query.refetch().then((res) => {
            if (!res.data) {
                throw new Error("No traceback data available");
            }
            return res.data;
        });

        const blob = new Blob([data.join("\n")], { type: "text/plain" });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.setAttribute("download", `${id}.task-traceback.txt`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
    };

    return { ...query, download };
};

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
