import { useMutation } from "@tanstack/react-query";
import apiClient from "../services/apiClient";
import { type Task } from "../models/api/responses/task";
import { type ValidateRecordsData } from "../models/api/requests/validation";

// -------------------------
// Mutations
// -------------------------
export const useValidateRecords = () =>
    useMutation<Task, Error, ValidateRecordsData>({
        mutationFn: async (data: ValidateRecordsData) =>
            (await apiClient.post<Task>("/validation/task", data)).data,
        onSuccess: () => {
            // TODO: Show notification
        },
    });
