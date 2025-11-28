import { useMutation, useQuery } from "@tanstack/react-query";
import apiClient, { setAuthToken } from "../services/apiClient";
import type { Me } from "../models/api/responses/users";
import { useCallback } from "react";
import type { EnforcedPermission } from "../models/ui/permissions";
import type { Token } from "../models/api/responses/auth";
import type { LoginUser, RegisterUser } from "../models/api/requests/auth";
import { queryClient } from "../services/queryClient";
import { useNotification } from "./useNotifications";
import type { AxiosError } from "axios";

// -------------------------
// Queries
// -------------------------
export const useGetMe = (enabled = true) =>
    useQuery<Me>({
        queryKey: ["auth", "me"],
        queryFn: async () =>
            apiClient.get<Me>(`/auth/me`).then((res) => res.data),
        enabled,
    });

export function useHasAccess() {
    const { data: me, isLoading } = useGetMe();

    const hasAccess = useCallback(
        (permission: EnforcedPermission) => {
            if (isLoading || !me) return undefined;

            if (typeof permission === "object") {
                if ("any" in permission) {
                    return permission.any.some((perm) =>
                        me.permissions.includes(perm)
                    );
                }
                if ("all" in permission) {
                    return permission.all.every((perm) =>
                        me.permissions.includes(perm)
                    );
                }
            }

            return me.permissions.includes(permission);
        },
        [me, isLoading]
    );

    return { isLoading, hasAccess };
}

// -------------------------
// Mutations
// -------------------------
export const useLogin = () => {
    const { addNotification } = useNotification();

    return useMutation<Token, Error, LoginUser>({
        mutationFn: async ({ username, password }) => {
            const formData = new URLSearchParams();
            formData.append("username", username);
            formData.append("password", password);

            return (
                await apiClient.post<Token>("/auth/login", formData, {
                    headers: {
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                })
            ).data;
        },
        onSuccess: (tokenData) => {
            localStorage.setItem("auth_token", tokenData.access_token);
            apiClient.defaults.headers.common[
                "Authorization"
            ] = `Bearer ${tokenData.access_token}`;
            // Notify
            addNotification({
                key: `login-success-${Date.now()}`,
                title: "Login Successful",
                variant: "success",
                timestamp: new Date().toISOString(),
                description: `You have successfully logged in.`,
                isNotificationRead: false,
            });
            // Invalidate
            queryClient.invalidateQueries({
                queryKey: ["auth"],
                exact: true,
            });
        },
    });
};

export const useLogout = () => {
    const logout = useCallback(() => {
        setAuthToken(null);
        queryClient.invalidateQueries({ queryKey: ["auth"], exact: true });
        queryClient.removeQueries({ queryKey: ["auth"] });
        window.location.href = "/";
    }, [queryClient]);

    return logout;
};

export const useSignUp = () => {
    const { addNotification } = useNotification();

    return useMutation<void, AxiosError<{ detail: string }>, RegisterUser>({
        mutationFn: async (data) => await apiClient.post("/auth/sign-up", data),
        onSuccess: (_, userData) => {
            addNotification({
                key: `signup-success-${Date.now()}`,
                title: "Registration Successful",
                variant: "success",
                timestamp: new Date().toISOString(),
                description: `Welcome, ${userData.first_name} ${userData.last_name}! Your account has been created successfully.`,
                isNotificationRead: false,
            });
            // Invalidate
            queryClient.invalidateQueries({
                queryKey: ["auth"],
                exact: true,
            });
        },
        onError: (error) => {
            console.error("Registration error:", error);
            addNotification({
                key: `signup-error-${Date.now()}`,
                title: "Registration Failed",
                variant: "danger",
                timestamp: new Date().toISOString(),
                description: `Error: ${error.response?.data.detail}`,
                isNotificationRead: false,
            });
        },
    });
};
