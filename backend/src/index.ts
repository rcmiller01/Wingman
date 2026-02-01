import express, { Request, Response, NextFunction } from 'express';
import cors from 'cors';
import { config, hasCloudLLM, hasProxmox } from './config/index.js';
import { prisma } from './db/client.js';
import { inventoryRouter, logRouter, incidentRouter, actionRouter, memoryRouter, logCompressor } from './routes/index.js';
import { startCollector, stopCollector } from './collectors/index.js';
import { startDetector, stopDetector } from './detectors/index.js';
import { qdrantService } from './memory/qdrant-client.js';

// Initialize Express app
const app = express();

// Middleware
app.use(cors());
app.use(express.json());

// =============================================================================
// Health Endpoints
// =============================================================================

// Basic health check
app.get('/health', (_req: Request, res: Response) => {
    res.json({ status: 'ok' });
});

// Readiness check
app.get('/ready', async (_req: Request, res: Response) => {
    const checks: Record<string, boolean | string> = {
        db: false,
        qdrant: false,
        cloudLlm: hasCloudLLM() ? 'configured' : 'not_configured',
        ollamaModel: config.ollamaModel,
        proxmox: hasProxmox() ? 'configured' : 'not_configured',
    };

    try {
        await prisma.$queryRaw`SELECT 1`;
        checks.db = true;
    } catch (error) {
        checks.db = false;
    }

    try {
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
        phase: 5,
        capabilities: {
            proxmox: hasProxmox(),
            cloudLlm: hasCloudLLM(),
            localLlm: config.ollamaModel,
        },
    });
});

app.use('/api/inventory', inventoryRouter);
app.use('/api/logs', logRouter);
app.use('/api/incidents', incidentRouter);
app.use('/api/actions', actionRouter);
app.use('/api/memory', memoryRouter);

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
        await prisma.$connect();
        console.log('✅ Database connected');

        startCollector();
        startDetector();
        await qdrantService.init();
        logCompressor.start();

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
    stopDetector();
    logCompressor.stop();
    await prisma.$disconnect();
    process.exit(0);
});

process.on('SIGTERM', async () => {
    stopCollector();
    stopDetector();
    logCompressor.stop();
    await prisma.$disconnect();
    process.exit(0);
});

main();
