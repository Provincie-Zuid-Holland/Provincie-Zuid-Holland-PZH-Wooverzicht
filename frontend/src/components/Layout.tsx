"use client";

import React, { useState, useCallback, useRef } from "react";
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
import { useHelpDialog } from "@/hooks/useHelpDialog";
import SearchBar from "./SearchBar";
import FilterPanel from "./FilterPanel";
import DocumentList from "./DocumentList";
import SidePanel from "./SidePanel";
import HelpButton from "./HelpButton";
import HelpDialog from "./HelpDialog";

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

    // Add flag to prevent duplicate searches
    const isSearchingRef = useRef(false);

    const { data, loading, error, search, clearResults } = useSearch();
    const { isOpen: isHelpOpen, openHelp, closeHelp } = useHelpDialog();

    // Core search function that always uses explicit filters
    const executeSearch = useCallback(
        async (query: string, filters: SearchFilters) => {
            // Prevent duplicate searches
            if (isSearchingRef.current) {
                console.log("🚫 Search already in progress, skipping duplicate");
                return;
            }

            console.log(`🔍 Starting search for: "${query}" with filters:`, filters);
            isSearchingRef.current = true;

            try {
                setCurrentQuery(query);
                if (!query.trim()) {
                    clearResults();
                    return;
                }
                await search(query, filters);
            } finally {
                // Always reset the flag
                isSearchingRef.current = false;
                console.log(`✅ Search completed for: "${query}"`);
            }
        },
        [search, clearResults]
    );

    // Handle search from search bar - uses current filters
    const handleSearch = useCallback(
        async (query: string) => {
            await executeSearch(query, currentFilters);
        },
        [executeSearch, currentFilters]
    );

    // Handle filter changes - optionally re-search with new filters
    const handleFiltersChange = useCallback(
        (filters: SearchFilters) => {
            console.log(`🎛️ Filters changed:`, filters);
            setCurrentFilters(filters);

            // Only re-search if we're not already searching AND there's a query
            if (!isSearchingRef.current && currentQuery.trim()) {
                console.log(`🔄 Re-searching with new filters`);
                executeSearch(currentQuery, filters);
            } else if (isSearchingRef.current) {
                console.log(`⏳ Search in progress, filters will apply to next search`);
            } else {
                console.log(`📝 Filters updated, no active query to re-search`);
            }
        },
        [currentQuery, executeSearch]
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
                            <Box
                                sx={{
                                    mb: 3,
                                    display: "flex",
                                    alignItems: "center",
                                    gap: 0
                                }}
                            >
                                <HelpButton onClick={openHelp} />
                                <Box sx={{ flex: 1 }}>
                                    <SearchBar
                                        onSearch={handleSearch}
                                        loading={loading}
                                        initialValue={currentQuery}
                                    />
                                </Box>
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

            {/* Help Dialog */}
            <HelpDialog
                open={isHelpOpen}
                onClose={closeHelp}
            />

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