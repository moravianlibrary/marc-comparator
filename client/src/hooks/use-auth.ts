import { useMutation, useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/api-client";
import { queryClient } from "@/lib/query-client";
import type { LoginRequest, RegisterRequest, MeResponse } from "@/types/auth";

export function useGetMe(enabled = true) {
  return useQuery<MeResponse>({
    queryKey: ["auth", "me"],
    queryFn: () => apiClient.get<MeResponse>("/auth/me").then((r) => r.data),
    enabled,
  });
}

export function useLogin() {
  return useMutation<void, Error, LoginRequest>({
    mutationFn: async ({ email, password }) => {
      await apiClient.post("/auth/login", { email, password });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["auth"] });
    },
  });
}

export function useSignUp() {
  return useMutation<void, Error, RegisterRequest>({
    mutationFn: (data) => apiClient.post("/auth/sign-up", data),
  });
}

export function useLogout() {
  return useMutation<void, Error, void>({
    mutationFn: () => apiClient.post("/auth/logout"),
    onSuccess: () => {
      queryClient.clear();
      window.location.href = "/login";
    },
  });
}

export function useOidcEnabled() {
  return useQuery<{ enabled: boolean; default: boolean }>({
    queryKey: ["auth", "oidc", "enabled"],
    queryFn: () =>
      apiClient
        .get<{ enabled: boolean; default: boolean }>("/auth/oidc/enabled")
        .then((r) => r.data),
    staleTime: Infinity,
  });
}
