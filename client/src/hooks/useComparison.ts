import { useMutation } from "@tanstack/react-query";
import apiClient from "../services/apiClient";
import { type Task } from "../models/api/responses/task";
import { type CompareRecordsData } from "../models/api/requests/comparison";

// -------------------------
// Mutations
// -------------------------
export const useCompareRecords = () =>
    useMutation<Task, Error, CompareRecordsData>({
        mutationFn: async (data: CompareRecordsData) =>
            (await apiClient.post<Task>("/comparison/task", data)).data,
        onSuccess: () => {
            // TODO: Show notification
        },
    });
