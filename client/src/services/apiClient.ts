import axios, { AxiosError } from "axios";
import { useLocation } from "react-router";

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
        const location = useLocation();
        if (error.status === 401) {
            setAuthToken(null);
            window.location.href =
                "/login?redirect=" + encodeURIComponent(location.pathname);
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
