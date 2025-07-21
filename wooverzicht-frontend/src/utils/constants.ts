export const PROVINCES = [
    "Drenthe",
    "Flevoland",
    "Friesland",
    "Gelderland",
    "Groningen",
    "Limburg",
    "Noord-Brabant",
    "Noord-Holland",
    "Overijssel",
    "Utrecht",
    "Zeeland",
    "Zuid-Holland",
] as const;

export const DOCUMENT_TYPES = [
    "woo-verzoek",
    "besluit",
    "rapport",
    "brief",
    "notitie",
] as const;

export const SEARCH_PLACEHOLDER = "Zoek naar WOO-documenten...";

export const PROVINCE_COLORS: Record<string, string> = {
    "Noord-Brabant": "#ff4444",
    "Zuid-Holland": "#1976d2",
    "Noord-Holland": "#4caf50",
    "Gelderland": "#ff9800",
    "Utrecht": "#9c27b0",
    "Limburg": "#f44336",
    "Overijssel": "#2196f3",
    "Friesland": "#009688",
    "Groningen": "#795548",
    "Drenthe": "#607d8b",
    "Flevoland": "#e91e63",
    "Zeeland": "#3f51b5",
} as const;
