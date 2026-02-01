import express, { Request, Response, NextFunction } from 'express';
import cors from 'cors';
import { config, hasCloudLLM, hasProxmox } from './config/index.js';
import { prisma } from './db/client.js';
import { inventoryRouter, logRouter } from './routes/index.js';
import { startCollector, stopCollector } from './collectors/index.js';
import { LogCollector } from './collectors/log-collector.js';

// Initialize Express app
const app = express();

// Middleware
app.use(cors());
app.use(express.json());

// Initialize Log Collector (starts scheduled job)
const logCollector = new LogCollector();

// =============================================================================
// Health Endpoints
// =============================================================================

// Basic health check - always returns ok if server is running
app.get('/health', (_req: Request, res: Response) => {
    res.json({ status: 'ok' });
});

// Readiness check - verifies database and external service connections
app.get('/ready', async (_req: Request, res: Response) => {
    const checks: Record<string, boolean | string> = {
        db: false,
        qdrant: false,
        cloudLlm: hasCloudLLM() ? 'configured' : 'not_configured',
        ollamaModel: config.ollamaModel,
        proxmox: hasProxmox() ? 'configured' : 'not_configured',
    };

    try {
        // Check database connection
        await prisma.$queryRaw`SELECT 1`;
        checks.db = true;
    } catch (error) {
        checks.db = false;
    }

    try {
        // Check Qdrant connection
        const qdrantResponse = await fetch(`${config.qdrantUrl}/collections`);
        checks.qdrant = qdrantResponse.ok;
    } catch (error) {
        checks.qdrant = false;
    }

    const allCriticalServicesUp = checks.db && checks.qdrant;

    res.status(allCriticalServicesUp ? 200 : 503).json({
        status: allCriticalServicesUp ? 'ready' : 'degraded',
        checks,
    });
});

// =============================================================================
// API Routes
// =============================================================================

app.get('/api/info', (_req: Request, res: Response) => {
    res.json({
        name: 'Homelab Copilot',
        version: '0.1.0',
        phase: 1,
        capabilities: {
            proxmox: hasProxmox(),
            cloudLlm: hasCloudLLM(),
            localLlm: config.ollamaModel,
        },
    });
});

// Mount inventory routes
app.use('/api/inventory', inventoryRouter);
// Mount logs routes
app.use('/api/logs', logRouter);

// =============================================================================
// Error Handler
// =============================================================================

app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
    console.error('Unhandled error:', err);
    res.status(500).json({
        error: 'Internal server error',
        message: config.nodeEnv === 'development' ? err.message : undefined,
    });
});

// =============================================================================
// Start Server
// =============================================================================

async function main() {
    try {
        // Test database connection on startup
        await prisma.$connect();
        console.log('✅ Database connected');

        // Start fact collector
        startCollector();

        app.listen(config.port, () => {
            console.log(`🚀 Homelab Copilot backend listening on port ${config.port}`);
            console.log(`   Environment: ${config.nodeEnv}`);
            console.log(`   Cloud LLM: ${hasCloudLLM() ? 'configured' : 'not configured'}`);
            console.log(`   Local LLM: ${config.ollamaModel}`);
            console.log(`   Proxmox: ${hasProxmox() ? 'configured' : 'not configured'}`);
        });
    } catch (error) {
        console.error('❌ Failed to start server:', error);
        process.exit(1);
    }
}

// Handle graceful shutdown
process.on('SIGINT', async () => {
    console.log('\n🛑 Shutting down...');
    stopCollector();
    // Stop log collector (implicit via process exit, or needs method)
    await prisma.$disconnect();
    process.exit(0);
});

process.on('SIGTERM', async () => {
    stopCollector();
    await prisma.$disconnect();
    process.exit(0);
});

main();

