"use client";

import React from "react";
import {
    Card,
    CardContent,
    Typography,
    Box,
    IconButton,
} from "@mui/material";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import CalendarTodayIcon from "@mui/icons-material/CalendarToday";

import DescriptionIcon from "@mui/icons-material/Description";
import { Document } from "@/types/api";

interface DocumentCardProps {
    document: Document;
    onClick: (document: Document) => void;
}

export default function DocumentCard({
    document,
    onClick,
}: DocumentCardProps) {
    const { metadata } = document;

    const handleCardClick = () => {
        onClick(document);
    };

    const handleLinkClick = (e: React.MouseEvent) => {
        e.stopPropagation();
        window.open(metadata.url, "_blank");
    };


    const formatDateUTC = (date: Date) => {
        const day = String(date.getUTCDate()).padStart(2, "0");
        const month = String(date.getUTCMonth() + 1).padStart(2, "0"); // Months are 0-based
        const year = date.getUTCFullYear();
        return `${day}-${month}-${year}`;
    };

    return (
        <Card
            onClick={handleCardClick}
            sx={{
                display: "flex",
                width: "100%",
                minHeight: 120,
                transition: "all 0.2s ease-in-out",
                "&:hover": {
                    transform: "translateY(-2px)",
                },
            }}
        >
            <CardContent
                sx={{ flex: 1, p: 3, display: "flex", alignItems: "center" }}
            >
                <Box sx={{ flex: 1 }}>
                    {/* Header with title and external link */}
                    <Box
                        sx={{
                            display: "flex",
                            justifyContent: "space-between",
                            mb: 2,
                        }}
                    >
                        <Typography
                            variant="h6"
                            component="h3"
                            sx={{
                                fontWeight: 600,
                                fontSize: "1.1rem",
                                lineHeight: 1.3,
                                flex: 1,
                                mr: 1,
                                color: "text.primary",
                            }}
                        >
                            {metadata.titel || "Geen titel beschikbaar"}
                        </Typography>

                        <IconButton
                            size="small"
                            onClick={handleLinkClick}
                            sx={{
                                color: "primary.main",
                                "&:hover": {
                                    backgroundColor: "primary.light",
                                    color: "white",
                                },
                            }}
                        >
                            <OpenInNewIcon fontSize="small" />
                        </IconButton>
                    </Box>

                    {/* Document details in horizontal layout */}
                    <Box
                        sx={{
                            display: "flex",
                            alignItems: "center",
                            gap: 3,
                            flexWrap: "wrap",
                        }}
                    >
                        {/* Province tag */}
                        <img 
                            src={`/logos/${metadata.provincie.toLowerCase()}.png`}
                            alt={metadata.provincie}
                            style={{
                                height: "24px", // Small chip height
                                width: "auto", // Maintains aspect ratio
                                borderRadius: "12px", // Matches chip's rounded appearance
                                maxWidth: "120px", // Prevents it from getting too wide
                            }}
                        />

                        {metadata.datum && (
                            <Box
                                sx={{
                                    display: "flex",
                                    alignItems: "center",
                                    gap: 1,
                                }}
                            >
                                <CalendarTodayIcon
                                    sx={{
                                        fontSize: 16,
                                        color: "text.secondary",
                                    }}
                                />
                                <Typography
                                    variant="body2"
                                    color="text.secondary"
                                >
                                    {metadata.datum ? formatDateUTC(new Date(Number(metadata.datum) * 1000)) : "Onbekende datum"}
                                </Typography>
                            </Box>
                        )}

                        <Box
                            sx={{
                                display: "flex",
                                alignItems: "center",
                                gap: 1,
                            }}
                        >
                            <DescriptionIcon
                                sx={{ fontSize: 16, color: "text.secondary" }}
                            />
                            <Typography
                                variant="body2"
                                color="text.secondary"
                            >
                                {metadata.type}
                            </Typography>
                        </Box>

                        {document.relevance_score !== null && (
                            <Typography
                                variant="body2"
                                color="text.secondary"
                            >
                                Relevantie:{" "}
                                {(document.relevance_score * 100).toFixed(1)}%
                            </Typography>
                        )}
                    </Box>
                </Box>
            </CardContent>
        </Card>
    );
}
