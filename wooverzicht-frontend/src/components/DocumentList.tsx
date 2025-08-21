"use client";

import React from "react";
import { Typography, Box, Paper, CircularProgress } from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import { Document, SearchResponse } from "@/types/api";
import DocumentCard from "./DocumentCard";

interface DocumentListProps {
    data: SearchResponse | null;
    loading: boolean;
    error: string | null;
    onDocumentClick: (document: Document) => void;
}

export default function DocumentList({
    data,
    loading,
    error,
    onDocumentClick,
}: DocumentListProps) {
    // Loading state
    if (loading) {
        return (
            <Box
                sx={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    py: 8,
                }}
            >
                <CircularProgress
                    size={40}
                    sx={{ mb: 2 }}
                />
                <Typography
                    variant="body1"
                    color="text.secondary"
                >
                    Documenten zoeken...
                </Typography>
            </Box>
        );
    }

    // Error state
    if (error) {
        return (
            <Paper
                sx={{
                    p: 4,
                    textAlign: "center",
                    backgroundColor: "error.light",
                    color: "error.contrastText",
                }}
            >
                <ErrorOutlineIcon sx={{ fontSize: 48, mb: 2 }} />
                <Typography
                    variant="h6"
                    gutterBottom
                >
                    Er is een fout opgetreden
                </Typography>
                <Typography variant="body2">{error}</Typography>
            </Paper>
        );
    }

    // No search performed yet
    if (!data) {
        return (
            <Box
                sx={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    py: 8,
                    color: "text.secondary",
                }}
            >
                <SearchIcon sx={{ fontSize: 64, mb: 2, opacity: 0.5 }} />
                <Typography
                    variant="h6"
                    gutterBottom
                >
                    Begin met zoeken
                </Typography>
                <Typography
                    variant="body2"
                    sx={{ textAlign: "center", maxWidth: 400 }}
                >
                    Voer een zoekterm in om relevante WOO-documenten te vinden.
                    Bijvoorbeeld: &quot;Geef mij alle documenten over de wolf met betrekking tot faunaschade&quot;
                </Typography>
            </Box>
        );
    }

    // No results found
    if (data.documents.length === 0) {
        return (
            <Paper sx={{ p: 4, textAlign: "center" }}>
                <SearchIcon
                    sx={{ fontSize: 48, mb: 2, color: "text.secondary" }}
                />
                <Typography
                    variant="h6"
                    gutterBottom
                >
                    Geen documenten gevonden
                </Typography>
                <Typography
                    variant="body2"
                    color="text.secondary"
                >
                    Probeer andere zoektermen of pas de filters aan.
                </Typography>
            </Paper>
        );
    }

    // Results found
    return (
        <Box>
            {/* Results summary */}
            <Box sx={{ mb: 3 }}>
                <Typography
                    variant="h6"
                    gutterBottom
                >
                    Zoekresultaten voor: &quot;{data.query}&quot;
                </Typography>
                <Typography
                    variant="body2"
                    color="text.secondary"
                >
                    {data.total_documents} document
                    {data.total_documents !== 1 ? "en" : ""} gevonden
                    {data.total_chunks > 0 &&
                        ` (${data.total_chunks} tekstfragmenten)`}
                </Typography>
            </Box>

            {/* Document list */}
            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                {data.documents.map((document) => (
                    <DocumentCard
                        key={document.id}
                        document={document}
                        onClick={onDocumentClick}
                    />
                ))}
            </Box>
        </Box>
    );
}
