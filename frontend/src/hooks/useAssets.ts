import { useState, useEffect } from "react";

import { getAssets } from "../services/assetService";
import type { Asset } from "../types/asset";

export function useAssets(page: number) {
    const [assets, setAssets] = useState<Asset[]>([]);
    const [count, setCount] = useState<number>(0);
    const [nextUrl, setNextUrl] = useState<string | null>(null);
    const [prevUrl, setPrevUrl] = useState<string | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    async function loadAssets() {
        try {
            setLoading(true);
            setError(null);

            const response = await getAssets(page);
            setAssets(response.results);
            setCount(response.count);
            setNextUrl(response.next);
            setPrevUrl(response.prev);
        } catch (error) {
            setError(String(error));
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        loadAssets();
    }, [page]);

    return { assets, count, nextUrl, prevUrl, loading, error };
}