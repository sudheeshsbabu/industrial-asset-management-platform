import type { ReactNode } from "react";

import {
    Stack,
    Typography
} from "@mui/material"

interface HeaderProps {
    title: string;
    actions?: ReactNode;
}

export default function Header({ title, actions }: HeaderProps) {
    return (
        <Stack
            direction="row"
            justifyContent="space-between"
            alignItems="center"
            sx={{ mb: 3 }}
        >
            <Typography variant="h4">{title}</Typography>
            {actions}
        </Stack>
    );
}