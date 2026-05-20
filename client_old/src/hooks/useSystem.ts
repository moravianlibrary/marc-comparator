import { useQuery } from "@tanstack/react-query";
import apiClient from "../services/apiClient";
import { type SystemInfo } from "../models/api/responses/system";
import { useCreateTask } from "./useTasks";

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
    useCreateTask<void>("/system/recreate-indexes");
