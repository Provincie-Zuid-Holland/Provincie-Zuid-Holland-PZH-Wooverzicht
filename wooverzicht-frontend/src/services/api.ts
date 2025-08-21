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

// Track ongoing requests to prevent duplicates
const ongoingRequests = new Map<string, Promise<SearchResponse>>();

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
    // Create a unique key for this request
    const requestKey = `search:${request.query}:${JSON.stringify(request.filters)}`;

    // Check if this exact request is already ongoing
    if (ongoingRequests.has(requestKey)) {
        console.log(`🔄 Reusing ongoing request for: ${request.query}`);
        return await ongoingRequests.get(requestKey)!;
    }

    console.log(`🚀 New search request: ${request.query}`);

    try {
        const requestPromise = apiClient.post<SearchResponse>(
            "/api/query/documents",
            {
                query: request.query,
                filters: request.filters
            }
        ).then(response => response.data);

        // Store the promise to prevent duplicates
        ongoingRequests.set(requestKey, requestPromise);

        const result = await requestPromise;

        // Clean up after completion
        ongoingRequests.delete(requestKey);

        return result;

    } catch (error) {
        // Clean up on error
        ongoingRequests.delete(requestKey);

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