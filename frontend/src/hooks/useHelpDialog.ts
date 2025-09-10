import { useState, useEffect } from "react";

const HELP_SHOWN_SESSION_KEY = "woo_help_shown_session";

export function useHelpDialog() {
    const [isOpen, setIsOpen] = useState(false);
    const [hasShownInitially, setHasShownInitially] = useState(false);

    useEffect(() => {
        // Check if help has been shown in this session
        const hasShownInSession = sessionStorage.getItem(HELP_SHOWN_SESSION_KEY);

        if (!hasShownInSession && !hasShownInitially) {
            // Show help dialog automatically on first visit in this session
            setIsOpen(true);
            setHasShownInitially(true);
            // Mark as shown in this session
            sessionStorage.setItem(HELP_SHOWN_SESSION_KEY, "true");
        }
    }, [hasShownInitially]);

    const openHelp = () => {
        setIsOpen(true);
    };

    const closeHelp = () => {
        setIsOpen(false);
    };

    return {
        isOpen,
        openHelp,
        closeHelp,
    };
}