import {
    useMutation,
    useQueries,
    useQuery,
    type UseQueryResult,
} from "@tanstack/react-query";
import apiClient from "../services/apiClient";
import { type EsQuery } from "../models/api/requests/es_query";
import {
    EsHitTaskSchema,
    SearchTasksResponseSchema,
    TaskSchema,
    type EsHitTask,
    type SearchTasksResponse,
    type Task,
    type TracebackLinesRequestParams,
} from "../models/api/responses/task";
import type { EsRequest } from "../models/api/requests/es";
import { useNotification } from "./useNotifications";
import { queryClient } from "../services/queryClient";

// -------------------------
// Queries
// -------------------------
export const useSearchTasks = (
    request: EsRequest,
    enabled = true,
    target: "all" | "own" = "own"
) =>
    useQuery<SearchTasksResponse>({
        queryKey: ["tasks", "search", request],
        queryFn: async () =>
            SearchTasksResponseSchema.parse(
                (await apiClient.post(`/tasks/search-${target}`, request)).data
            ),
        enabled,
    });

export const useGetTask = (
    id: string,
    enabled = true,
    target: "all" | "own" = "own"
) =>
    useQuery<EsHitTask | undefined>({
        queryKey: ["tasks", "get", id],
        queryFn: async () => {
            const hit = (
                await apiClient.post(`/tasks/search-${target}`, {
                    query: { term: { _id: id } },
                })
            ).data?.hits?.hits?.[0];

            if (!hit) return undefined;

            const parsed = EsHitTaskSchema.safeParse(hit);
            if (!parsed.success) {
                throw new Error("Failed to parse task data");
            }
            return parsed.data;
        },
        enabled,
    });

export const useSearchTasksBatch = (
    requests: EsRequest[],
    enabled = true,
    target: "all" | "own" = "own"
): UseQueryResult<SearchTasksResponse>[] =>
    useQueries({
        queries: requests.map((request, idx) => ({
            queryKey: ["tasks", "search", idx, request],
            queryFn: async () =>
                SearchTasksResponseSchema.parse(
                    (await apiClient.post(`/tasks/search-${target}`, request))
                        .data
                ),
            enabled,
        })),
    });

export const useGetUserActiveTasks = (enabled = true) =>
    useQuery<SearchTasksResponse>({
        queryKey: ["tasks", "running", "own"],
        queryFn: async () =>
            SearchTasksResponseSchema.parse(
                (
                    await apiClient.post(`/tasks/search-own`, {
                        query: {
                            bool: {
                                should: [
                                    { term: { status: "Pending" } },
                                    { term: { status: "Started" } },
                                ],
                                minimum_should_match: 1,
                            },
                        },
                    })
                ).data
            ),
        enabled,
    });

export const useGetTraceback = (
    id: string,
    params: TracebackLinesRequestParams | null = null,
    enabled = true
) =>
    useQuery<string>({
        queryKey: ["tasks", "traceback", id, params],
        queryFn: async () =>
            (
                await apiClient.get<string>(`/tasks/${id}/traceback`, {
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

        const blob = new Blob([data], { type: "text/plain" });
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
            // Invalidate queries
            queryClient.invalidateQueries({
                queryKey: ["tasks"],
                exact: false,
            });
        },
    });
};

// -------------------------
// Mutations
// -------------------------
export const useRevokeTask = () =>
    useMutation<Task, Error, string>({
        mutationFn: async (id: string) =>
            (await apiClient.patch<Task>(`/tasks/${id}/revoke`)).data,
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["tasks"],
                exact: false,
            });
        },
    });

export const useDeleteTasks = () => useCreateTask<EsQuery>("/tasks/delete");
