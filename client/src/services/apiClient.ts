import axios, { AxiosError } from "axios";

const apiClient = axios.create({
    baseURL: "/api",
    headers: { "Content-Type": "application/json" },
});

apiClient.interceptors.response.use(
    (response) => response,
    (error: AxiosError) => {
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
