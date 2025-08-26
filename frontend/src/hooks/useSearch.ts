import { useState, useCallback } from "react";
import { SearchResponse, SearchRequest, SearchFilters } from "@/types/api";
import { searchDocuments } from "@/services/api";

interface UseSearchReturn {
    data: SearchResponse | null;
    loading: boolean;
    error: string | null;
    search: (query: string, filters?: SearchFilters) => Promise<void>;
    clearResults: () => void;
}

export function useSearch(): UseSearchReturn {
    const [data, setData] = useState<SearchResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const search = useCallback(
        async (query: string, filters?: SearchFilters) => {
            if (!query.trim()) {
                setData(null);
                setError(null);
                return;
            }

            setLoading(true);
            setError(null);

            try {
                const request: SearchRequest = {
                    query: query.trim(),
                    filters,
                };

                const response = await searchDocuments(request);
                setData(response);
            } catch (err) {
                setError(
                    err instanceof Error ? err.message : "An error occurred"
                );
                setData(null);
            } finally {
                setLoading(false);
            }
        },
        []
    );

    const clearResults = useCallback(() => {
        setData(null);
        setError(null);
    }, []);

    return {
        data,
        loading,
        error,
        search,
        clearResults,
    };
}
