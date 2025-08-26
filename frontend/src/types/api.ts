export interface DocumentMetadata {
    url: string;
    provincie: string;
    titel: string;
    datum: string;
    type: string;
    publiekssamenvatting: string;
    file_name: string;
    file_type: string;
}

export interface Chunk {
    id: string;
    content: string;
    relevance_score: number | null;
    metadata: DocumentMetadata;
}

export interface Document {
    id: string;
    metadata: DocumentMetadata;
    relevance_score: number | null;
}

export interface SearchResponse {
    success: boolean;
    query: string;
    chunks: Chunk[];
    documents: Document[];
    total_chunks: number;
    total_documents: number;
    error?: string;
}

export interface SearchFilters {
    provinces: string[];
    startDate: string | null;
    endDate: string | null;
}

export interface SearchRequest {
    query: string;
    filters?: SearchFilters;
}
