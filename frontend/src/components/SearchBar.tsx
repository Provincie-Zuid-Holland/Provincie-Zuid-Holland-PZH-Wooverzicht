"use client";

import React, { useState, KeyboardEvent } from "react";
import { TextField, InputAdornment, IconButton, Box, Button, Tooltip } from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import ClearIcon from "@mui/icons-material/Clear";
import { SEARCH_PLACEHOLDER } from "@/utils/constants";

interface SearchBarProps {
    onSearch: (query: string) => void;
    loading?: boolean;
    initialValue?: string;
}

export default function SearchBar({
    onSearch,
    loading = false,
    initialValue = "",
}: SearchBarProps) {
    const [query, setQuery] = useState(initialValue);

    const handleSearch = () => {
        if (query.trim()) {
            onSearch(query.trim());
        }
    };

    const handleKeyPress = (event: KeyboardEvent<HTMLInputElement>) => {
        if (event.key === "Enter") {
            handleSearch();
        }
    };

    const handleClear = () => {
        setQuery("");
        onSearch("");
    };

    return (
        <Box sx={{ width: "100%", maxWidth: 800, mx: "auto" }}>
            <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
                <Tooltip title="Deze zoekmachine werkt het beste als je volledige vragen stelt en zoveel mogelijk context geeft. Bijv: 'Geef mij alle documenten over de wolf met betrekking tot faunaschade'" arrow>
                    <TextField
                        fullWidth
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder={SEARCH_PLACEHOLDER}
                        disabled={loading}
                        InputProps={{
                            startAdornment: (
                                <InputAdornment position="start">
                                    <SearchIcon color="action" />
                                </InputAdornment>
                            ),
                            endAdornment: query && (
                                <InputAdornment position="end">
                                    <IconButton
                                        size="small"
                                        onClick={handleClear}
                                        disabled={loading}
                                        sx={{ mr: 1 }}
                                        aria-label="Clear search"
                                    >
                                        <ClearIcon />
                                    </IconButton>
                                </InputAdornment>
                            ),
                        }}
                        sx={{
                            "& .MuiOutlinedInput-root": {
                                backgroundColor: "background.paper",
                                fontSize: "1.1rem",
                                height: "56px",
                                "&:hover": {
                                    "& .MuiOutlinedInput-notchedOutline": {
                                        borderColor: "primary.main",
                                    },
                                },
                            },
                        }}
                    />
                </Tooltip>
                <Button
                    variant="contained"
                    onClick={handleSearch}
                    disabled={loading || !query.trim()}
                    startIcon={<SearchIcon />}
                    sx={{
                        height: "56px",
                        minWidth: "120px",
                        px: 3,
                        fontSize: "1rem",
                        fontWeight: 500,
                    }}
                    aria-label="Search documents"
                >
                    Zoeken
                </Button>
            </Box>
        </Box>
    );
}