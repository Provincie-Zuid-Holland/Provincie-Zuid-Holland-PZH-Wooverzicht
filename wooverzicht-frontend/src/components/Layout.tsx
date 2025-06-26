"use client";

import React, { useState, useCallback } from "react";
import {
    Box,
    Container,
    Typography,
    AppBar,
    Toolbar,
    Paper,
    Alert,
    useTheme,
    useMediaQuery,
} from "@mui/material";
import { Document, SearchFilters } from "@/types/api";
import { useSearch } from "@/hooks/useSearch";
import SearchBar from "./SearchBar";
import FilterPanel from "./FilterPanel";
import DocumentList from "./DocumentList";
import SidePanel from "./SidePanel";

export default function Layout() {
    const theme = useTheme();
    const isMobile = useMediaQuery(theme.breakpoints.down("md"));

    const [selectedDocument, setSelectedDocument] = useState<Document | null>(
        null
    );
    const [currentFilters, setCurrentFilters] = useState<SearchFilters>({
        provinces: [],
        startDate: "1970-01-01",
        endDate: "2200-01-01",
    });
    const [currentQuery, setCurrentQuery] = useState<string>("");

    const { data, loading, error, search, clearResults } = useSearch();

    const handleSearch = useCallback(
        async (query: string) => {
            setCurrentQuery(query);
            if (!query.trim()) {
                clearResults();
                return;
            }
            await search(query, currentFilters);
        },
        [search, clearResults, currentFilters]
    );

    const handleFiltersChange = useCallback(
        (filters: SearchFilters) => {
            setCurrentFilters(filters);
            // Re-search with new filters if there's an active query
            if (currentQuery.trim()) {
                search(currentQuery, filters);
            }
        },
        [search, currentQuery]
    );

    const handleDocumentClick = useCallback((document: Document) => {
        setSelectedDocument(document);
    }, []);

    const handleCloseSidePanel = useCallback(() => {
        setSelectedDocument(null);
    }, []);

    return (
        <Box
            sx={{ minHeight: "100vh", backgroundColor: "background.default" }}
        >
            {/* Header */}
            <AppBar
                position="static"
                elevation={0}
                sx={{ backgroundColor: "white" }}
            >
                <Toolbar sx={{ py: 2 }}>
                    <Container maxWidth="lg">
                        <Typography
                            variant="h4"
                            component="h1"
                            sx={{
                                fontWeight: 700,
                                color: "primary.main",
                                textAlign: "center",
                                fontSize: { xs: "1.8rem", md: "2.5rem" },
                            }}
                        >
                            W👀verzicht
                        </Typography>
                    </Container>
                </Toolbar>
            </AppBar>

            {/* Main Content with Sidebar Layout */}
            <Box sx={{ display: "flex", minHeight: "calc(100vh - 88px)" }}>
                {/* Main Content Area */}
                <Box
                    sx={{
                        flex: 1,
                        transition: "margin-right 0.3s ease-in-out",
                        marginRight:
                            selectedDocument && !isMobile ? "480px" : 0,
                    }}
                >
                    <Container
                        maxWidth="lg"
                        sx={{ py: 4 }}
                    >
                        {/* Search Section */}
                        <Paper
                            elevation={2}
                            sx={{
                                p: 4,
                                mb: 4,
                                backgroundColor: "background.paper",
                            }}
                        >
                            <Box sx={{ mb: 3 }}>
                                <SearchBar
                                    onSearch={handleSearch}
                                    loading={loading}
                                    initialValue={currentQuery}
                                />
                            </Box>

                            <FilterPanel
                                onFiltersChange={handleFiltersChange}
                                disabled={loading}
                            />
                        </Paper>

                        {/* Error Alert */}
                        {error && (
                            <Alert
                                severity="error"
                                sx={{ mb: 3 }}
                            >
                                {error}
                            </Alert>
                        )}

                        {/* Results Section */}
                        <DocumentList
                            data={data}
                            loading={loading}
                            error={error}
                            onDocumentClick={handleDocumentClick}
                        />
                    </Container>
                </Box>
            </Box>

            {/* Desktop Fixed Position Side Panel */}
            {!isMobile && selectedDocument && (
                <Box
                    sx={{
                        position: "fixed",
                        top: 88, // Height of header
                        right: 0,
                        width: 480,
                        height: "calc(100vh - 88px)",
                        backgroundColor: "background.paper",
                        boxShadow: "-2px 0 8px rgba(0,0,0,0.1)",
                        zIndex: 1200,
                        overflow: "auto",
                    }}
                >
                    <SidePanel
                        open={!!selectedDocument}
                        document={selectedDocument}
                        searchData={data}
                        onClose={handleCloseSidePanel}
                        variant="persistent"
                    />
                </Box>
            )}

            {/* Mobile Side Panel */}
            {isMobile && (
                <SidePanel
                    open={!!selectedDocument}
                    document={selectedDocument}
                    searchData={data}
                    onClose={handleCloseSidePanel}
                    variant="temporary"
                />
            )}

            {/* Footer */}
            <Box
                component="footer"
                sx={{
                    mt: 8,
                    py: 4,
                    backgroundColor: "background.paper",
                    borderTop: "1px solid",
                    borderColor: "grey.200",
                }}
            >
                <Container maxWidth="lg">
                    <Typography
                        variant="body2"
                        color="text.secondary"
                        textAlign="center"
                    >
                        Deze applicatie is ontwikkeld om WOO-verzoeken
                        efficiënter te verwerken. Voor vragen of ondersteuning,
                        neem contact op met de beheerder.
                    </Typography>
                </Container>
            </Box>
        </Box>
    );
}
