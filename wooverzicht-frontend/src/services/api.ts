import axios from "axios";
import { SearchResponse, SearchRequest } from "@/types/api";

const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        "Content-Type": "application/json",
    },
    timeout: 30000000,
});

// Add request interceptor for logging
apiClient.interceptors.request.use(
    (config) => {
        console.log(
            `API Request: ${config.method?.toUpperCase()} ${config.url}`
        );
        return config;
    },
    (error) => Promise.reject(error)
);

// Add response interceptor for error handling
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        console.error("API Error:", error.response?.data || error.message);
        return Promise.reject(error);
    }
);

export const searchDocuments = async (
    request: SearchRequest
): Promise<SearchResponse> => {
    try {
        const response = await apiClient.post<SearchResponse>(
            "/api/query/documents",
            {
                query: request.query,
                // Note: Filters not implemented in backend yet
                // filters: request.filters
            }
        );

        return response.data;
    } catch (error) {
        if (axios.isAxiosError(error)) {
            throw new Error(error.response?.data?.error || error.message);
        }
        throw new Error("An unexpected error occurred");
    }
};

export const healthCheck = async (): Promise<{
    status: string;
    timestamp: string;
}> => {
    try {
        const response = await apiClient.get("/api/health");
        return response.data;
    } catch (error) {
        if (axios.isAxiosError(error)) {
            throw new Error(error.response?.data?.error || error.message);
        }
        throw new Error("Health check failed");
    }
};
