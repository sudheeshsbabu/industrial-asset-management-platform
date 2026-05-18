import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import {
    Card,
    CardContent,
    Container,
    Typography,
} from '@mui/material';

import type { Asset } from '../types/asset';
import { getAssetById } from '../services/assetService';

function AssetDetailPage() {
    const { id } = useParams();
    const [asset, setAsset] = useState<Asset | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const loadAsset = async () => {
        try {
            setLoading(true);
            const data = await getAssetById(Number(id));
            setAsset(data);
        } catch (error) {
            setError("Failed to fetch asset")
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        loadAsset();
    }, []);

    if (loading) return <Typography>Loading</Typography>

    if (error) return <Typography>Error: {error}</Typography>

    if (!asset) return <Typography>Asset not found</Typography>

    return (
        <Container sx={{ mt: 4 }}>
            <Card>
                <CardContent>
                    <Typography variant="h4" gutterBottom>
                        {asset.name}
                    </Typography>
                    <Typography variant="h6">
                        Site: {asset.site}
                    </Typography>
                    <Typography variant="h6">
                        Status: {asset.status}
                    </Typography>
                </CardContent>
            </Card>
        </Container>
    )
}

export default AssetDetailPage;