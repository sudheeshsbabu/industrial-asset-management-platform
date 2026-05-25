import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Container, Typography, Button, Stack } from "@mui/material";
import { DataGrid, type GridColDef } from '@mui/x-data-grid'

import Header from "../components/common/Header";
import { useAssets } from "../hooks/useAssets";

function AssetsPage() {
    const navigate = useNavigate();
    const [page, setPage] = useState<number>(1);
    const { assets, count, nextUrl, prevUrl, loading, error } = useAssets(page);

    const columns: GridColDef[] = [
        {
            field: "id",
            headerName: "ID",
        },
        {
            field: "name",
            headerName: "Name",
            flex: 1
        },
        {
            field: "site",
            headerName: "Site",
            flex: 1
        },
        {
            field: "status",
            headerName: "Status",
            flex: 1
        },
        {
            field: "actions",
            headerName: "Actions",
            renderCell: (params) => (
                <Button
                    variant="outlined"
                    onClick={() => navigate(`/assets/${params.row.id}`)}
                >
                    View
                </Button>
            )
        }
    ]
    return (
        <Container>
            <Header
                title="Assets"
                actions={
                    <Button
                        variant="contained"
                        onClick={() => navigate("/assets/create")}
                    >
                        Add Asset
                    </Button>
                }
            />
            <Typography sx={{ mt: 3 }}>
                Total Assets: {count}
            </Typography>
            {loading && <Typography>Loading...</Typography>}
            {!loading && (
                <>
                    <DataGrid
                        columns={columns}
                        rows={assets}
                        disableRowSelectionOnClick
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
                </>
            )}
            {error && <Typography color="error">{error}</Typography>}
        </Container>
    )
}

export default AssetsPage;