import { useState, useEffect } from "react";
import { Container, Typography, Button, Stack } from "@mui/material";
import { DataGrid, type GridColDef } from '@mui/x-data-grid'

import type { Asset, PaginatedResponse } from "../types/asset"

function AssetsPage() {
    const [assets, setAssets] = useState<Asset[]>([]);
    const [count, setCount] = useState<number>(0);
    const [page, setPage] = useState<number>(1);
    const [nextUrl, setNextUrl] = useState<string | null>(null);
    const [prevUrl, setPrevUrl] = useState<string | null>(null);
    useEffect(() => {
        async function loadAssets() {
            const response = await fetch(`http://localhost:8080/assets?page=${page}&page_size=10`)
            const data: PaginatedResponse<Asset> = await response.json();
            setAssets(data.results);
            setCount(data.count);
            setNextUrl(data.next);
            setPrevUrl(data.prev);
        }
        loadAssets();
    }, [page]);

    const columns: GridColDef[] = [
        {
            field: "id",
            headerName: "ID",
            width: 50
        },
        {
            field: "name",
            headerName: "Name",
            width: 200
        },
        {
            field: "site",
            headerName: "Site",
            width: 200
        },
        {
            field: "status",
            headerName: "Status",
            width: 100
        }
    ]
    return (
        <Container>
            <Stack
                component="div"
                direction="row"
                sx={{
                    justifyContent: "space-between",
                    alignItems: "center",
                    mt: 4
                }}
            >
                <Typography variant="h4">Assets</Typography>
                <Button variant="contained">Add Asset</Button>
            </Stack>
            <Typography sx={{ mt: 3 }}>
                Total Assets: {count}
            </Typography>
            <DataGrid
                columns={columns}
                rows={assets}
                // disableRowSelectionOnClick
                hideFooter
            />
            <Stack
                direction="row"
                spacing={2}
                sx={{ mt: 2 }}
            >
                <Button
                    variant="contained"
                    disabled={!prevUrl}
                    onClick={() => setPage(page - 1)}
                >
                    Previous
                </Button>
                <Typography>Page: {page}</Typography>
                <Button
                    variant="contained"
                    disabled={!nextUrl}
                    onClick={() => setPage(page + 1)}
                >
                    Next
                </Button>
            </Stack>
        </Container>
    )
}

export default AssetsPage;