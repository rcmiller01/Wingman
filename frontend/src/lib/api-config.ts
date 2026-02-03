/**
 * API Configuration
 * Central configuration for backend API endpoints
 */

export const API_CONFIG = {
    baseUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    endpoints: {
        health: '/api/health',
        inventory: '/api/inventory',
        logs: '/api/logs',
        facts: '/api/facts',
        incidents: '/api/incidents',
        plans: '/api/plans',
        rag: '/api/rag',
        todos: '/api/todos',
        settings: '/api/settings',
    },
} as const;

/**
 * Helper to build full API URL
 */
export function getApiUrl(path: string): string {
    return `${API_CONFIG.baseUrl}${path}`;
}
