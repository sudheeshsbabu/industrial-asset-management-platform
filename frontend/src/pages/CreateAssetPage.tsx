import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
    Button,
    Container,
    Stack,
    TextField,
    Typography
} from "@mui/material";

import { createAsset } from "../services/assetService";
import Header from "../components/common/Header"


function AssetDetailPage() {
    const navigate = useNavigate();
    const [name, setName] = useState('');
    const [site, setSite] = useState('');
    const [status, setStatus] = useState('active');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            const createdAsset = await createAsset({ name, site, status });
            navigate(`/assets/${createdAsset.data.id}`);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to create asset");
        } finally {
            setLoading(false);
        }
    }
    return (
        <Container sx={{ mt: 4 }}>
            <Header
                title="Create New Asset"
                actions={
                    <Button
                        variant="contained"
                        onClick={() => navigate("/")}
                    >
                        Assets
                    </Button>
                }
            />
            <form onSubmit={handleSubmit}>
                <Stack spacing={2}>
                    <TextField
                        label="Asset Name"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        required
                    />
                    <TextField
                        label="Asset Site"
                        value={site}
                        onChange={(e) => setSite(e.target.value)}
                        required
                    />
                    <TextField
                        label="Asset Status"
                        value={status}
                        onChange={(e) => setStatus(e.target.value)}
                        required
                    />
                    <Button
                        type="submit"
                        variant="contained"
                        disabled={loading}
                    >
                        Create Asset
                    </Button>
                </Stack>
            </form>
            {error && (
                <Typography color="error" sx={{ mt: 2 }}>
                    {error}
                </Typography>
            )}
        </Container>
    )
}

export default AssetDetailPage;