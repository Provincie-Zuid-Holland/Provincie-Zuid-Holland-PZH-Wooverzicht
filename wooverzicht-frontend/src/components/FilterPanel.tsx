"use client";

import React, { useState, useEffect } from "react";
import {
    Box,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
    Chip,
    OutlinedInput,
    SelectChangeEvent,
    Button,
    Typography,
    Divider,
} from "@mui/material";
import { LocalizationProvider } from "@mui/x-date-pickers";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import dayjs, { Dayjs } from "dayjs";
import "dayjs/locale/nl";
import FilterListIcon from "@mui/icons-material/FilterList";
import ClearIcon from "@mui/icons-material/Clear";
import { PROVINCES } from "@/utils/constants";
import { SearchFilters } from "@/types/api";

// Set Dutch locale for dayjs
dayjs.locale("nl");

interface FilterPanelProps {
    onFiltersChange: (filters: SearchFilters) => void;
    disabled?: boolean;
}

const ITEM_HEIGHT = 48;
const ITEM_PADDING_TOP = 8;
const MenuProps = {
    PaperProps: {
        style: {
            maxHeight: ITEM_HEIGHT * 4.5 + ITEM_PADDING_TOP,
            width: 250,
        },
    },
};

export default function FilterPanel({
    onFiltersChange,
    disabled = false,
}: FilterPanelProps) {
    const [selectedProvinces, setSelectedProvinces] = useState<string[]>([]);
    const [startDate, setStartDate] = useState<Dayjs | null>(null);
    const [endDate, setEndDate] = useState<Dayjs | null>(null);

    // Update parent when filters change
    useEffect(() => {
        const filters: SearchFilters = {
            provinces: selectedProvinces,
            startDate: startDate?.format("YYYY-MM-DD") || null,
            endDate: endDate?.format("YYYY-MM-DD") || null,
        };
        onFiltersChange(filters);
    }, [selectedProvinces, startDate, endDate, onFiltersChange]);

    const handleProvinceChange = (
        event: SelectChangeEvent<typeof selectedProvinces>
    ) => {
        const value = event.target.value;
        setSelectedProvinces(
            typeof value === "string" ? value.split(",") : value
        );
    };

    const handleClearFilters = () => {
        setSelectedProvinces([]);
        setStartDate(null);
        setEndDate(null);
    };

    const hasActiveFilters =
        selectedProvinces.length > 0 || startDate || endDate;

    return (
        <LocalizationProvider
            dateAdapter={AdapterDayjs}
            adapterLocale="nl"
        >
            <Box
                sx={{
                    display: "flex",
                    gap: 2,
                    alignItems: "center",
                    flexWrap: "wrap",
                    p: 2,
                    backgroundColor: "background.paper",
                    borderRadius: 1,
                    border: "1px solid",
                    borderColor: "grey.200",
                }}
            >
                <Typography
                    variant="body2"
                    sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: 1,
                        color: "text.secondary",
                        minWidth: "fit-content",
                    }}
                >
                    <FilterListIcon fontSize="small" />
                    Filters:
                </Typography>

                <FormControl
                    size="small"
                    sx={{ minWidth: 200 }}
                >
                    <InputLabel>Provincies</InputLabel>
                    <Select
                        multiple
                        value={selectedProvinces}
                        onChange={handleProvinceChange}
                        input={<OutlinedInput label="Provincies" />}
                        renderValue={(selected) => (
                            <Box
                                sx={{
                                    display: "flex",
                                    flexWrap: "wrap",
                                    gap: 0.5,
                                }}
                            >
                                {selected.map((value) => (
                                    <Chip
                                        key={value}
                                        label={value}
                                        size="small"
                                    />
                                ))}
                            </Box>
                        )}
                        MenuProps={MenuProps}
                        disabled={disabled}
                    >
                        {PROVINCES.map((province) => (
                            <MenuItem
                                key={province}
                                value={province}
                            >
                                {province}
                            </MenuItem>
                        ))}
                    </Select>
                </FormControl>

                <DatePicker
                    label="Begin datum"
                    value={startDate}
                    onChange={setStartDate}
                    disabled={disabled}
                    slotProps={{
                        textField: {
                            size: "small",
                            sx: { width: 160 },
                        },
                    }}
                    maxDate={endDate || undefined}
                />

                <DatePicker
                    label="Eind datum"
                    value={endDate}
                    onChange={setEndDate}
                    disabled={disabled}
                    slotProps={{
                        textField: {
                            size: "small",
                            sx: { width: 160 },
                        },
                    }}
                    minDate={startDate || undefined}
                />

                {hasActiveFilters && (
                    <>
                        <Divider
                            orientation="vertical"
                            flexItem
                        />
                        <Button
                            startIcon={<ClearIcon />}
                            onClick={handleClearFilters}
                            size="small"
                            disabled={disabled}
                            sx={{ color: "text.secondary" }}
                        >
                            Wissen
                        </Button>
                    </>
                )}
            </Box>
        </LocalizationProvider>
    );
}
