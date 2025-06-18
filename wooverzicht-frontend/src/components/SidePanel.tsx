"use client";

import React, { useMemo } from "react";
import {
    Drawer,
    Typography,
    Box,
    IconButton,
    Button,
    Chip,
    Accordion,
    AccordionSummary,
    AccordionDetails,
    Paper,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import CalendarTodayIcon from "@mui/icons-material/CalendarToday";
import LocationOnIcon from "@mui/icons-material/LocationOn";
import DescriptionIcon from "@mui/icons-material/Description";
import { Document, SearchResponse } from "@/types/api";
import { PROVINCE_COLORS } from "@/utils/constants";

interface SidePanelProps {
    open: boolean;
    document: Document | null;
    searchData: SearchResponse | null;
    onClose: () => void;
    variant?: "persistent" | "temporary";
}

export default function SidePanel({
    open,
    document,
    searchData,
    onClose,
    variant = "temporary",
}: SidePanelProps) {
    // Find chunks that belong to this document
    const documentChunks = useMemo(() => {
        if (!document || !searchData) return [];

        return searchData.chunks.filter(
            (chunk) => chunk.metadata.titel === document.metadata.titel
        );
    }, [document, searchData]);

    if (!document) return null;

    const { metadata } = document;
    const provinceColor = PROVINCE_COLORS[metadata.provincie] || "#666";

    const formatDate = (dateString: string) => {
        try {
            const date = new Date(dateString.split("-").reverse().join("-"));
            return date.toLocaleDateString("nl-NL", {
                day: "2-digit",
                month: "2-digit",
                year: "numeric",
            });
        } catch {
            return dateString;
        }
    };

    const handleOpenDocument = () => {
        window.open(metadata.url, "_blank");
    };

    // For persistent variant (desktop), render content directly
    if (variant === "persistent") {
        return (
            <Box
                sx={{
                    display: "flex",
                    flexDirection: "column",
                    height: "100%",
                }}
            >
                {/* Header */}
                <Box
                    sx={{
                        p: 3,
                        borderBottom: "1px solid",
                        borderColor: "grey.200",
                        backgroundColor: "background.paper",
                    }}
                >
                    <Box
                        sx={{
                            display: "flex",
                            justifyContent: "space-between",
                            mb: 2,
                        }}
                    >
                        <Typography
                            variant="h6"
                            component="h2"
                            sx={{ flex: 1, mr: 2 }}
                        >
                            Document Details
                        </Typography>
                        <IconButton
                            onClick={onClose}
                            size="small"
                        >
                            <CloseIcon />
                        </IconButton>
                    </Box>

                    <Chip
                        label={metadata.provincie}
                        size="small"
                        sx={{
                            backgroundColor: provinceColor,
                            color: "white",
                            fontWeight: 500,
                            mb: 2,
                        }}
                    />

                    <Typography
                        variant="h5"
                        component="h1"
                        sx={{
                            fontWeight: 600,
                            lineHeight: 1.3,
                            mb: 2,
                        }}
                    >
                        {metadata.titel || "Geen titel beschikbaar"}
                    </Typography>

                    <Button
                        startIcon={<OpenInNewIcon />}
                        onClick={handleOpenDocument}
                        variant="contained"
                        size="small"
                        fullWidth
                    >
                        Ga naar de website van {metadata.provincie}
                    </Button>
                </Box>

                {/* Content */}
                <Box sx={{ flex: 1, overflow: "auto", p: 3 }}>
                    {/* Document Information */}
                    <Paper sx={{ p: 2, mb: 3, backgroundColor: "grey.50" }}>
                        <Typography
                            variant="subtitle1"
                            fontWeight={600}
                            gutterBottom
                        >
                            Document Informatie
                        </Typography>

                        <Box
                            sx={{
                                display: "flex",
                                flexDirection: "column",
                                gap: 1.5,
                            }}
                        >
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
                                    <Typography variant="body2">
                                        <strong>Besloten op:</strong>{" "}
                                        {formatDate(metadata.datum)}
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
                                <LocationOnIcon
                                    sx={{
                                        fontSize: 16,
                                        color: "text.secondary",
                                    }}
                                />
                                <Typography variant="body2">
                                    <strong>Provincie:</strong>{" "}
                                    {metadata.provincie}
                                </Typography>
                            </Box>

                            <Box
                                sx={{
                                    display: "flex",
                                    alignItems: "center",
                                    gap: 1,
                                }}
                            >
                                <DescriptionIcon
                                    sx={{
                                        fontSize: 16,
                                        color: "text.secondary",
                                    }}
                                />
                                <Typography variant="body2">
                                    <strong>Type:</strong> {metadata.type}
                                </Typography>
                            </Box>

                            {document.relevance_score !== null && (
                                <Typography variant="body2">
                                    <strong>Relevantie Score:</strong>{" "}
                                    {(document.relevance_score * 100).toFixed(
                                        1
                                    )}
                                    %
                                </Typography>
                            )}
                        </Box>
                    </Paper>

                    {/* Text Fragments */}
                    {documentChunks.length > 0 && (
                        <Box>
                            <Typography
                                variant="subtitle1"
                                fontWeight={600}
                                gutterBottom
                            >
                                Tekstfragmenten ({documentChunks.length})
                            </Typography>

                            {documentChunks.map((chunk, index) => (
                                <Accordion
                                    key={chunk.id}
                                    sx={{ mb: 1 }}
                                >
                                    <AccordionSummary
                                        expandIcon={<ExpandMoreIcon />}
                                    >
                                        <Typography
                                            variant="body2"
                                            fontWeight={500}
                                        >
                                            Tekstfragment {index + 1}
                                            {chunk.relevance_score && (
                                                <Chip
                                                    label={`${(
                                                        chunk.relevance_score *
                                                        100
                                                    ).toFixed(1)}%`}
                                                    size="small"
                                                    sx={{ ml: 1, height: 20 }}
                                                />
                                            )}
                                        </Typography>
                                    </AccordionSummary>
                                    <AccordionDetails>
                                        <Typography
                                            variant="body2"
                                            sx={{
                                                lineHeight: 1.6,
                                                whiteSpace: "pre-wrap",
                                                backgroundColor: "grey.50",
                                                p: 2,
                                                borderRadius: 1,
                                                border: "1px solid",
                                                borderColor: "grey.200",
                                            }}
                                        >
                                            {chunk.content}
                                        </Typography>
                                    </AccordionDetails>
                                </Accordion>
                            ))}
                        </Box>
                    )}

                    {documentChunks.length === 0 && (
                        <Paper
                            sx={{
                                p: 3,
                                textAlign: "center",
                                backgroundColor: "grey.50",
                            }}
                        >
                            <Typography
                                variant="body2"
                                color="text.secondary"
                            >
                                Geen tekstfragmenten beschikbaar voor dit
                                document.
                            </Typography>
                        </Paper>
                    )}
                </Box>
            </Box>
        );
    }

    // For temporary variant (mobile), use Drawer
    return (
        <Drawer
            anchor="right"
            open={open}
            onClose={onClose}
            sx={{
                "& .MuiDrawer-paper": {
                    width: "100%",
                    maxWidth: "100vw",
                },
            }}
        >
            <Box
                sx={{
                    display: "flex",
                    flexDirection: "column",
                    height: "100%",
                }}
            >
                {/* Header */}
                <Box
                    sx={{
                        p: 3,
                        borderBottom: "1px solid",
                        borderColor: "grey.200",
                        backgroundColor: "background.paper",
                    }}
                >
                    <Box
                        sx={{
                            display: "flex",
                            justifyContent: "space-between",
                            mb: 2,
                        }}
                    >
                        <Typography
                            variant="h6"
                            component="h2"
                            sx={{ flex: 1, mr: 2 }}
                        >
                            Document Details
                        </Typography>
                        <IconButton
                            onClick={onClose}
                            size="small"
                        >
                            <CloseIcon />
                        </IconButton>
                    </Box>

                    <Chip
                        label={metadata.provincie}
                        size="small"
                        sx={{
                            backgroundColor: provinceColor,
                            color: "white",
                            fontWeight: 500,
                            mb: 2,
                        }}
                    />

                    <Typography
                        variant="h5"
                        component="h1"
                        sx={{
                            fontWeight: 600,
                            lineHeight: 1.3,
                            mb: 2,
                        }}
                    >
                        {metadata.titel || "Geen titel beschikbaar"}
                    </Typography>

                    <Button
                        startIcon={<OpenInNewIcon />}
                        onClick={handleOpenDocument}
                        variant="contained"
                        size="small"
                        fullWidth
                    >
                        Ga naar de website van {metadata.provincie}
                    </Button>
                </Box>

                {/* Content */}
                <Box sx={{ flex: 1, overflow: "auto", p: 3 }}>
                    {/* Document Information */}
                    <Paper sx={{ p: 2, mb: 3, backgroundColor: "grey.50" }}>
                        <Typography
                            variant="subtitle1"
                            fontWeight={600}
                            gutterBottom
                        >
                            Document Informatie
                        </Typography>

                        <Box
                            sx={{
                                display: "flex",
                                flexDirection: "column",
                                gap: 1.5,
                            }}
                        >
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
                                    <Typography variant="body2">
                                        <strong>Besloten op:</strong>{" "}
                                        {formatDate(metadata.datum)}
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
                                <LocationOnIcon
                                    sx={{
                                        fontSize: 16,
                                        color: "text.secondary",
                                    }}
                                />
                                <Typography variant="body2">
                                    <strong>Provincie:</strong>{" "}
                                    {metadata.provincie}
                                </Typography>
                            </Box>

                            <Box
                                sx={{
                                    display: "flex",
                                    alignItems: "center",
                                    gap: 1,
                                }}
                            >
                                <DescriptionIcon
                                    sx={{
                                        fontSize: 16,
                                        color: "text.secondary",
                                    }}
                                />
                                <Typography variant="body2">
                                    <strong>Type:</strong> {metadata.type}
                                </Typography>
                            </Box>

                            {document.relevance_score !== null && (
                                <Typography variant="body2">
                                    <strong>Relevantie Score:</strong>{" "}
                                    {(document.relevance_score * 100).toFixed(
                                        1
                                    )}
                                    %
                                </Typography>
                            )}
                        </Box>
                    </Paper>

                    {/* Text Fragments */}
                    {documentChunks.length > 0 && (
                        <Box>
                            <Typography
                                variant="subtitle1"
                                fontWeight={600}
                                gutterBottom
                            >
                                Tekstfragmenten ({documentChunks.length})
                            </Typography>

                            {documentChunks.map((chunk, index) => (
                                <Accordion
                                    key={chunk.id}
                                    sx={{ mb: 1 }}
                                >
                                    <AccordionSummary
                                        expandIcon={<ExpandMoreIcon />}
                                    >
                                        <Typography
                                            variant="body2"
                                            fontWeight={500}
                                        >
                                            Tekstfragment {index + 1}
                                            {chunk.relevance_score && (
                                                <Chip
                                                    label={`${(
                                                        chunk.relevance_score *
                                                        100
                                                    ).toFixed(1)}%`}
                                                    size="small"
                                                    sx={{ ml: 1, height: 20 }}
                                                />
                                            )}
                                        </Typography>
                                    </AccordionSummary>
                                    <AccordionDetails>
                                        <Typography
                                            variant="body2"
                                            sx={{
                                                lineHeight: 1.6,
                                                whiteSpace: "pre-wrap",
                                                backgroundColor: "grey.50",
                                                p: 2,
                                                borderRadius: 1,
                                                border: "1px solid",
                                                borderColor: "grey.200",
                                            }}
                                        >
                                            {chunk.content}
                                        </Typography>
                                    </AccordionDetails>
                                </Accordion>
                            ))}
                        </Box>
                    )}

                    {documentChunks.length === 0 && (
                        <Paper
                            sx={{
                                p: 3,
                                textAlign: "center",
                                backgroundColor: "grey.50",
                            }}
                        >
                            <Typography
                                variant="body2"
                                color="text.secondary"
                            >
                                Geen tekstfragmenten beschikbaar voor dit
                                document.
                            </Typography>
                        </Paper>
                    )}
                </Box>
            </Box>
        </Drawer>
    );
}
