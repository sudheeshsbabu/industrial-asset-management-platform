export interface Asset {
    id: number,
    name: string,
    site: string,
    status: string
}

export interface PaginatedResponse<T> {
    results: T[],
    count: number,
    page: number,
    page_size: number,
    prev: string | null,
    next: string | null
}