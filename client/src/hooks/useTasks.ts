import { useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "../services/apiClient";
import { type EsQuery } from "../models/api/requests/es_query";
import { type Task } from "../models/api/responses/task";

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
