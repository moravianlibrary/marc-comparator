import axios, { AxiosError } from "axios";

const apiClient = axios.create({
    baseURL: "/api",
    headers: { "Content-Type": "application/json" },
});

export const setAuthToken = (token: string | null) => {
    if (token) {
        localStorage.setItem("auth_token", token);
        apiClient.defaults.headers.common["Authorization"] = `Bearer ${token}`;
    } else {
        localStorage.removeItem("auth_token");
        delete apiClient.defaults.headers.common["Authorization"];
    }
};

setAuthToken(localStorage.getItem("auth_token"));

apiClient.interceptors.response.use(
    (response) => response,
    (error: AxiosError) => {
        if (error.status === 401) {
            const currentPath = window.location.pathname;

            setAuthToken(null);
            window.location.href =
                "/login?redirect=" + encodeURIComponent(currentPath);
            return Promise.reject(error);
        }
        if (error.status === 403) {
            window.location.href = "/home?error=forbidden";
            return Promise.reject(error);
        }
        if (error.response) {
            console.error(
                "Server error:",
                error.response.status,
                error.response.data
            );
        } else if (error.request) {
            console.error("No response received:", error.request);
        } else {
            console.error("Axios error:", error.message);
        }

        return Promise.reject(error);
    }
);

export default apiClient;
