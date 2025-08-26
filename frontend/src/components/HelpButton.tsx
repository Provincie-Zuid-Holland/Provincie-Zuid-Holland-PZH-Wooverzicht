"use client";

import React from "react";
import { IconButton, Tooltip } from "@mui/material";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";

interface HelpButtonProps {
    onClick: () => void;
}

export default function HelpButton({ onClick }: HelpButtonProps) {
    return (
        <Tooltip title="Help & uitleg" placement="top">
            <IconButton
                onClick={onClick}
                size="large"
                sx={{
                    color: "primary.main",
                    "&:hover": {
                        backgroundColor: "primary.light",
                        color: "primary.dark",
                    },
                    mr: 2, // Add margin to the right to space it from the search bar
                }}
                aria-label="Open help dialog"
            >
                <HelpOutlineIcon />
            </IconButton>
        </Tooltip>
    );
}