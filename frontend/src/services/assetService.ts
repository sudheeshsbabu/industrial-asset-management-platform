import type {
    Asset,
    AssetResponse,
    PaginatedResponse
} from "../types/asset";

export async function getAssets(
    page: number,
    pageSize: number = 10
): Promise<PaginatedResponse<Asset>> {

    const apiUrl = `http://localhost:8080/assets?page=${page}&page_size=${pageSize}`;
    const response = await fetch(apiUrl);
    return response.json();
}

export async function getAssetById(
    id: number
): Promise<Asset> {
    const apiUrl = `http://localhost:8080/assets/${id}`;
    const response = await fetch(apiUrl);
    return response.json();
}

export async function createAsset(
    asset: Partial<Asset>,
): Promise<AssetResponse> {
    const apiUrl = `http://localhost:8080/assets`;
    const response = await fetch(apiUrl, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(asset),
    });
    return response.json();
}