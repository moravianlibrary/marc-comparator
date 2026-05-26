import axios from "axios";

const apiClient = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});

let isRefreshing = false;
let refreshQueue: Array<{
  resolve: (value: unknown) => void;
  reject: (reason: unknown) => void;
}> = [];

function processQueue(error: unknown) {
  refreshQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error);
    } else {
      resolve(undefined);
    }
  });
  refreshQueue = [];
}

function dispatchApiError(status: number, url: string, message: string) {
  window.dispatchEvent(
    new CustomEvent("api-error", {
      detail: {
        status,
        url,
        message,
        timestamp: new Date().toISOString(),
      },
    })
  );
}

async function isBackendHealthy(): Promise<boolean> {
  try {
    const response = await axios.get("/api/system/health", { timeout: 3000 });
    return response.status === 200;
  } catch {
    return false;
  }
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url?.endsWith("/auth/refresh")
    ) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          refreshQueue.push({ resolve, reject });
        }).then(() => apiClient(originalRequest));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        await apiClient.post("/auth/refresh");
        processQueue(null);
        return apiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError);
        const currentPath = window.location.pathname;
        if (currentPath !== "/login" && currentPath !== "/signup") {
          window.location.href =
            "/login?redirect=" + encodeURIComponent(currentPath);
        }
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    if (error.response?.status === 401) {
      const currentPath = window.location.pathname;
      if (currentPath !== "/login" && currentPath !== "/signup") {
        window.location.href =
          "/login?redirect=" + encodeURIComponent(currentPath);
      }
      return Promise.reject(error);
    }

    // --- Non-401 error handling ---
    const status = error.response?.status;
    if (status && status >= 400) {
      // Skip health check if the failing request is the health endpoint itself
      const url = originalRequest.url || "";
      if (!url.endsWith("/system/health")) {
        const healthy = await isBackendHealthy();
        if (!healthy) {
          const redirect = window.location.pathname + window.location.search;
          window.location.href =
            "/service-unavailable?redirect=" + encodeURIComponent(redirect);
          return Promise.reject(error);
        }
      }

      // Backend is healthy but this request failed — show error toast
      const message =
        error.response?.data?.detail ||
        error.response?.statusText ||
        "Unknown error";
      dispatchApiError(status, url, message);
    }

    return Promise.reject(error);
  }
);

export default apiClient;
