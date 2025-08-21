"use client";

import React from "react";
import { ThemeProvider } from "@mui/material/styles";
import CssBaseline from "@mui/material/CssBaseline";
import { theme } from "@/theme/theme";

interface ThemeProviderWrapperProps {
    children: React.ReactNode;
}

export default function ThemeProviderWrapper({
    children,
}: ThemeProviderWrapperProps) {
    return (
        <ThemeProvider theme={theme}>
            <CssBaseline />
            {children}
        </ThemeProvider>
    );
}
