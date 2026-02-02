export function getApiUrl(path: string): string {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || '/api';
    // Ensure path starts with / if not present (unless path is empty)
    const normalizedPath = path.startsWith('/') ? path : `/${path}`;
    // Removing trailing slash from baseUrl if present to avoid double slashes
    const normalizedBase = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;
    return `${normalizedBase}${normalizedPath}`;
}
