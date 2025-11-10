import { useMutation } from "@tanstack/react-query";
import apiClient from "../services/apiClient";
import { type Task } from "../models/api/responses/task";
import { type AuthorityLinkingData } from "../models/api/requests/authority_linking";

// -------------------------
// Mutations
// -------------------------
export const useLinkToAuthorities = () =>
    useMutation<Task, Error, AuthorityLinkingData>({
        mutationFn: async (data: AuthorityLinkingData) =>
            (await apiClient.post<Task>("/authority-linking/task", data)).data,
        onSuccess: () => {
            // TODO: Show notification
        },
    });
