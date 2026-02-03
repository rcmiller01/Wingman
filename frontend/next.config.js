/** @type {import('next').NextConfig} */
const nextConfig = {
    output: 'standalone',
    reactStrictMode: true,
    async rewrites() {
        // Rewrite /api/* to backend for both client-side and SSR requests
        // In Docker: backend is reachable at http://backend:8000
        // In development: backend is at http://localhost:8000
        const backendUrl = process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        return [
            {
                source: '/api/:path*',
                destination: `${backendUrl}/api/:path*`,
            },
        ];
    },
};

module.exports = nextConfig;
