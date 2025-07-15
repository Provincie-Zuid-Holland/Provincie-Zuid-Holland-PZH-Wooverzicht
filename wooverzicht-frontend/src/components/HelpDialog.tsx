"use client";

import React from "react";
import {
    Dialog,
    DialogTitle,
    DialogContent,
    IconButton,
    Typography,
    Box,
    useTheme,
    useMediaQuery,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";

interface HelpDialogProps {
    open: boolean;
    onClose: () => void;
}

export default function HelpDialog({ open, onClose }: HelpDialogProps) {
    const theme = useTheme();
    const isMobile = useMediaQuery(theme.breakpoints.down("md"));

    return (
        <Dialog
            open={open}
            onClose={onClose}
            maxWidth="md"
            fullWidth
            fullScreen={isMobile}
            PaperProps={{
                sx: {
                    borderRadius: isMobile ? 0 : 2,
                    maxHeight: isMobile ? "100vh" : "90vh",
                },
            }}
        >
            <DialogTitle
                sx={{
                    m: 0,
                    p: 3,
                    display: "flex",
                    flexDirection: "row",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    borderBottom: 1,
                    borderColor: "divider",
                }}
            >
                <Box>
                    <Typography variant="h5" component="div" fontWeight={600}>
                        How-to-use guide
                    </Typography>
                    <Typography
                        variant="subtitle1"
                        sx={{
                            fontStyle: "italic",
                            color: "text.secondary",
                            fontSize: "1.1rem",
                            mt: 1,
                        }}
                    >
                        Zo gebruik je de Woo-zoekmachine
                    </Typography>
                </Box>
                <IconButton
                    aria-label="close"
                    onClick={onClose}
                    sx={{ color: "grey.500" }}
                >
                    <CloseIcon />
                </IconButton>
            </DialogTitle>


            <DialogContent sx={{ p: 0 }}>
                <Box sx={{ p: 3, pb: 4 }}>
                    {/* Section: Zoeken op soortgelijke termen */}
                    <Box sx={{ mb: 4 }}>
                        <Typography
                            variant="h6"
                            component="h3"
                            fontWeight={600}
                            sx={{ mb: 2, color: "primary.main" }}
                        >
                            Zoeken op soortgelijke termen
                        </Typography>
                        <Typography variant="body1" sx={{ lineHeight: 1.7 }}>
                            In de zoekbalk kun je een trefwoord invoeren (bijv. &ldquo;windmolens&rdquo;,
                            &ldquo;stikstofbeleid&rdquo;). De zoekmachine vindt niet alleen exacte matches,
                            maar ook inhoudelijk soortgelijke verzoeken. Zo kun je ontdekken of
                            anderen eerder een soortgelijk Woo-verzoek hebben opgevraagd, ook als
                            ze andere woorden gebruikten.
                        </Typography>
                    </Box>

                    {/* Section: Zoeken op volledig Woo-verzoek */}
                    <Box sx={{ mb: 4 }}>
                        <Typography
                            variant="h6"
                            component="h3"
                            fontWeight={600}
                            sx={{ mb: 2, color: "primary.main" }}
                        >
                            Zoeken op volledig Woo-verzoek
                        </Typography>
                        <Typography variant="body1" sx={{ lineHeight: 1.7 }}>
                            Daarnaast kan je in de zoekbalk ook een volledig Woo-verzoek van een
                            indiener plakken. De zoekmachine vergelijkt jouw zoekopdracht
                            automatisch met bestaande Woo-verzoeken en -documenten, en toont
                            overeenkomsten op basis van inhoudelijke gelijkenis.
                        </Typography>
                    </Box>

                    {/* Section: Filteren */}
                    <Box sx={{ mb: 4 }}>
                        <Typography
                            variant="h6"
                            component="h3"
                            fontWeight={600}
                            sx={{ mb: 2, color: "primary.main" }}
                        >
                            Filteren op provincie en periode
                        </Typography>
                        <Typography variant="body1" sx={{ lineHeight: 1.7, mb: 2 }}>
                            Gebruik de filters aan de zijkant of bovenaan de pagina om je
                            resultaten te verfijnen:
                        </Typography>
                        <Box component="ul" sx={{ ml: 2, "& li": { mb: 1 } }}>
                            <li>
                                <Typography variant="body1">
                                    <strong>Provincie:</strong> Selecteer één of meerdere provincies
                                    waarin je geïnteresseerd bent.
                                </Typography>
                            </li>
                            <li>
                                <Typography variant="body1">
                                    <strong>Periode:</strong> Stel een begindatum en einddatum in om
                                    alleen Woo-besluiten binnen een bepaalde tijdspanne te tonen.
                                </Typography>
                            </li>
                        </Box>
                    </Box>

                    {/* Section: Waarom deze resultaten */}
                    <Box sx={{ mb: 4 }}>
                        <Typography
                            variant="h6"
                            component="h3"
                            fontWeight={600}
                            sx={{ mb: 2, color: "primary.main" }}
                        >
                            Waarom deze resultaten? Fragmenten uit Woo-documenten
                        </Typography>
                        <Typography variant="body1" sx={{ lineHeight: 1.7 }}>
                            Bij elk zoekresultaat zie je tekstfragmenten uit de Woo-documenten
                            waar jouw zoekterm of vergelijkbare termen in voorkomen. Je kunt op
                            een resultaat klikken om te zien waarom het getoond wordt – bijvoorbeeld
                            een stukje tekst waar jouw onderwerp wordt besproken.
                        </Typography>
                    </Box>

                    {/* Section: Gebruik per check */}
                    <Box sx={{ mb: 4 }}>
                        <Typography
                            variant="h6"
                            component="h3"
                            fontWeight={600}
                            sx={{ mb: 2, color: "primary.main" }}
                        >
                            Gebruik per check (bij nieuwe Woo-verzoeken)
                        </Typography>
                        <Typography variant="body1" sx={{ lineHeight: 1.7, mb: 2 }}>
                            Deze zoekmachine is vooral handig bij drie soorten handelingen:
                        </Typography>
                        <Box component="ol" sx={{ ml: 2, "& li": { mb: 1.5 } }}>
                            <li>
                                <Typography variant="body1">
                                    <strong>Bestaande documenten vinden:</strong> Ontdek of er al
                                    documenten openbaar zijn gemaakt over jouw onderwerp, zodat je
                                    die kunt hergebruiken of specifieker kunt vragen.
                                </Typography>
                            </li>
                            <li>
                                <Typography variant="body1">
                                    <strong>Vergelijken met eerdere verzoeken:</strong> Check of jouw
                                    Woo-verzoek al eens eerder (deels) is ingediend.
                                </Typography>
                            </li>
                            <li>
                                <Typography variant="body1">
                                    <strong>Afwijzingsgronden achterhalen:</strong> Bekijk of provincies
                                    vergelijkbare verzoeken hebben afgewezen, en lees de motivering
                                    (bijvoorbeeld: privacy, veiligheid, onevenredige belasting).
                                </Typography>
                            </li>
                        </Box>
                    </Box>

                    {/* Section: Resultaten over provincies */}
                    <Box sx={{ mb: 4 }}>
                        <Typography
                            variant="h6"
                            component="h3"
                            fontWeight={600}
                            sx={{ mb: 2, color: "primary.main" }}
                        >
                            Resultaten over vijf provincies heen
                        </Typography>
                        <Typography variant="body1" sx={{ lineHeight: 1.7 }}>
                            De zoekmachine toont Woo-verzoeken van de provincies Flevoland,
                            Zuid-Holland, Gelderland, Overijssel en Noord-Brabant.
                        </Typography>
                    </Box>

                    {/* Section: Tip */}
                    <Box
                        sx={{
                            p: 3,
                            backgroundColor: "primary.light",
                            borderRadius: 2,
                            border: `1px solid ${theme.palette.primary.main}`,
                        }}
                    >
                        <Typography
                            variant="h6"
                            component="h3"
                            fontWeight={600}
                            sx={{ mb: 2, color: "primary.dark" }}
                        >
                            Tip
                        </Typography>
                        <Typography variant="body1" sx={{ lineHeight: 1.7, mb: 1 }}>
                            Gebruik deze zoekmachine om:
                        </Typography>
                        <Box component="ul" sx={{ ml: 2, "& li": { mb: 0.5 } }}>
                            <li>
                                <Typography variant="body1">
                                    Te voorkomen dat je dubbel werk doet
                                </Typography>
                            </li>
                            <li>
                                <Typography variant="body1">
                                    Je verzoek preciezer en gerichter te formuleren
                                </Typography>
                            </li>
                            <li>
                                <Typography variant="body1">
                                    Sneller toegang te krijgen tot reeds openbaar gemaakte informatie
                                </Typography>
                            </li>
                        </Box>
                    </Box>
                </Box>
            </DialogContent>
        </Dialog>
    );
}