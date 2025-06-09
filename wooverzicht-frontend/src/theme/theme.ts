import { createTheme } from "@mui/material/styles";

export const theme = createTheme({
    palette: {
        primary: {
            main: "#1976d2", // Blue from reference
            light: "#42a5f5",
            dark: "#1565c0",
        },
        secondary: {
            main: "#ff4444", // Red for province tags
            light: "#ff7777",
            dark: "#cc0000",
        },
        background: {
            default: "#f5f5f5",
            paper: "#ffffff",
        },
        text: {
            primary: "#333333",
            secondary: "#666666",
        },
        grey: {
            100: "#f5f5f5",
            200: "#eeeeee",
            300: "#e0e0e0",
            400: "#bdbdbd",
            500: "#9e9e9e",
        },
    },
    typography: {
        fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
        h1: {
            fontSize: "2rem",
            fontWeight: 600,
            color: "#333333",
        },
        h2: {
            fontSize: "1.5rem",
            fontWeight: 600,
            color: "#333333",
        },
        h3: {
            fontSize: "1.25rem",
            fontWeight: 600,
            color: "#333333",
        },
        body1: {
            fontSize: "0.9rem",
            lineHeight: 1.5,
        },
        body2: {
            fontSize: "0.8rem",
            lineHeight: 1.4,
            color: "#666666",
        },
    },
    components: {
        MuiCard: {
            styleOverrides: {
                root: {
                    boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
                    borderRadius: "8px",
                    "&:hover": {
                        boxShadow: "0 4px 16px rgba(0,0,0,0.15)",
                        cursor: "pointer",
                    },
                },
            },
        },
        MuiButton: {
            styleOverrides: {
                root: {
                    textTransform: "none",
                    borderRadius: "6px",
                    fontWeight: 500,
                },
            },
        },
        MuiTextField: {
            styleOverrides: {
                root: {
                    "& .MuiOutlinedInput-root": {
                        borderRadius: "8px",
                    },
                },
            },
        },
        MuiChip: {
            styleOverrides: {
                root: {
                    borderRadius: "16px",
                    fontSize: "0.75rem",
                    height: "24px",
                },
            },
        },
    },
});
