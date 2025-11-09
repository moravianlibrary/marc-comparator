import { useMutation, useQuery } from "@tanstack/react-query";
import apiClient from "../services/apiClient";
import { type Task } from "../models/api/responses/task";
import { type SystemInfo } from "../models/api/responses/system";

// -------------------------
// Queries
// -------------------------
export const useGetSystemInfo = (enabled = true) =>
    useQuery<SystemInfo>({
        queryKey: ["systemInfo"],
        queryFn: async () =>
            (await apiClient.get<SystemInfo>("/system/info")).data,
        enabled,
    });

// -------------------------
// Mutations
// -------------------------
export const useRecreateIndexes = () =>
    useMutation<Task, Error, void>({
        mutationFn: async () =>
            (await apiClient.post<Task>("/system/recreate-indexes")).data,
        onSuccess: () => {
            // TODO: Show notification
        },
    });
