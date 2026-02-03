/**
 * Build API URL for fetching.
 *
 * Always returns a relative URL that goes through the Next.js proxy.
 * This ensures both client-side and SSR requests work correctly.
 *
 * @param path - API path (e.g., '/incidents', '/settings/llm', 'todos')
 * @returns Relative URL with /api prefix (e.g., '/api/incidents')
 */
export function getApiUrl(path: string): string {
    // Normalize: ensure path starts with /
    let normalizedPath = path.startsWith('/') ? path : `/${path}`;

    // Ensure /api prefix (don't double-add if already present)
    if (!normalizedPath.startsWith('/api/') && !normalizedPath.startsWith('/api?')) {
        normalizedPath = `/api${normalizedPath}`;
    }

    // Return relative URL - Next.js rewrites will proxy to backend
    return normalizedPath;
}
