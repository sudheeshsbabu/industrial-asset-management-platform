export interface Asset {
    id: number,
    name: string,
    site: string,
    status: string
}

export interface PaginatedResponse<T> {
    results: T[],
    total_count: number,
    page: number,
    page_size: number,
    previous: string | null,
    next: string | null
}