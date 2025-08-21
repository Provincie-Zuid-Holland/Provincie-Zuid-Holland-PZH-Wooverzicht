import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import ThemeProviderWrapper from "@/components/ThemeProviderWrapper";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
    title: "Wooverzicht - WOO Document Search",
    description:
        "Search and explore WOO (Wet Open Overheid) documents from Dutch provinces",
    keywords: ["WOO", "open overheid", "documenten", "zoeken", "provincies"],
    authors: [{ name: "WOO Search Team" }],
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="nl">
            <body className={inter.className}>
                <ThemeProviderWrapper>{children}</ThemeProviderWrapper>
            </body>
        </html>
    );
}
