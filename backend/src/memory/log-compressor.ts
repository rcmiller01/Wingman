import fs from 'fs';
import path from 'path';
import { prisma } from '../db/client.js';
import { config } from '../config/index.js';
import { getContainerInfo } from '../adapters/docker.js';
import { schedule, ScheduledTask } from 'node-cron';
import { qdrantService } from './qdrant-client.js';

const KNOWLEDGE_PATH = process.env.KNOWLEDGE_PATH || path.join(process.cwd(), 'knowledge');

export class LogCompressor {
    private job: ScheduledTask | null = null;
    private isRunning = false;

    constructor() {
        // Run daily at midnight (0 0 * * *)
        // For MVP demo, run every 5 minutes or on demand
        // I'll set it to run every hour for now: '0 * * * *'
        this.job = schedule('0 * * * *', () => {
            this.compressAll();
        });
    }

    public start() {
        if (this.job) this.job.start();
        console.log('📚 Log Compressor scheduled (hourly)');
    }

    public stop() {
        if (this.job) this.job.stop();
    }

    /**
     * Trigger compression manually
     */
    public async compressNow() {
        return this.compressAll();
    }

    private async compressAll() {
        if (this.isRunning) {
            console.log('DEBUG: Compression skipped - Already running');
            return;
        }
        this.isRunning = true;
        console.log('DEBUG: Starting log compression cycle...');

        try {
            // 1. Get all resources with logs
            const resources = await prisma.log.groupBy({
                by: ['resourceRef'],
                _count: {
                    id: true
                }
            });
            console.log(`DEBUG: Found ${resources.length} resources with logs.`);

            for (const res of resources) {
                console.log(`DEBUG: Checking ${res.resourceRef} (${res._count.id} logs)...`);
                if (res._count.id > 0) { // arbitrary threshold
                    await this.processResource(res.resourceRef);
                }
            }
        } catch (error) {
            console.error('DEBUG: Compression cycle failed:', error);
        } finally {
            this.isRunning = false;
        }
    }

    private async processResource(resourceRef: string) {
        // Only verify docker for now
        if (!resourceRef.startsWith('docker://')) return;

        // Check if summary already exists for today
        const today = new Date();
        today.setHours(0, 0, 0, 0);

        console.log(`DEBUG: Checking existing summary for ${resourceRef}`);
        const existingSummary = await prisma.logSummaryDocument.findFirst({
            where: {
                resourceRef,
                periodStart: { gte: today }
            }
        });

        if (existingSummary) {
            if (existingSummary.summary === 'Failed to generate summary.') {
                console.log(`DEBUG: Previous summary failed for ${resourceRef}, retrying...`);
                await prisma.logSummaryDocument.delete({ where: { id: existingSummary.id } });
            } else {
                console.log(`DEBUG: Skipping ${resourceRef}, already summarized today (ID: ${existingSummary.id}).`);
                return;
            }
        }

        console.log(`📚 Compressing logs for ${resourceRef}...`);

        // Fetch logs
        const logs = await prisma.log.findMany({
            where: { resourceRef },
            orderBy: { timestamp: 'asc' },
            take: 1000 // Limit context
        });

        if (logs.length === 0) return;

        // Prepare context for LLM
        const logContext = logs.map(l => `[${l.timestamp.toISOString()}] [${l.logSource}] ${l.content}`).join('\n');

        // Generate Summary via Ollama
        const summary = await this.generateSummary(logContext);

        // Resolve Name for folder structure
        let resourceName = resourceRef;
        try {
            if (resourceRef.startsWith('docker://')) {
                const id = resourceRef.split('docker://')[1];
                const info = await getContainerInfo(id); // Using adapter
                // Fallback if container is gone? Adapter throws.
                // We'll trust adapter or catch error
                resourceName = info.name;
            }
        } catch (e) {
            // Container might be gone, use ID
            console.warn(`Could not resolve name for ${resourceRef}, using ID.`);
        }

        // Save Artifact
        await this.saveArtifact(resourceRef, resourceName, summary);

        // Save to Qdrant
        await qdrantService.storeMemory(summary, {
            resourceRef,
            resourceName,
            logStart: logs[0].timestamp,
            logEnd: logs[logs.length - 1].timestamp,
            type: 'log_summary'
        });

        // Save to DB
        await prisma.logSummaryDocument.create({
            data: {
                resourceRef,
                periodStart: logs[0].timestamp,
                periodEnd: logs[logs.length - 1].timestamp,
                summary,
                errorPatterns: {}, // TODO: structured extraction
                retentionDate: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000) // 1 year
            }
        });

        // Purge raw logs? 
        // For MVP, we keep them until retention policy (90 days).
    }

    private async generateSummary(logText: string): Promise<string> {
        const prompt = `
You are a DevOps assistant. Analyze the following logs.
Summarize the key events, errors, and patterns. 
Be concise. Use Markdown.
Identify any root causes for crashes or restarts.

Logs:
${logText}
        `;

        try {
            const response = await fetch(`${config.ollamaHost}/api/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model: config.ollamaModel,
                    prompt: prompt,
                    stream: false
                })
            });

            if (!response.ok) throw new Error(`Ollama API error: ${response.statusText}`);

            const data: any = await response.json();
            return data.response;
        } catch (error) {
            console.error('LLM summarization failed:', error);
            return 'Failed to generate summary.';
        }
    }

    private async saveArtifact(resourceRef: string, resourceName: string, content: string) {
        // Structure: knowledge/docker/<name>/summary_<date>.md
        const type = resourceRef.split('://')[0];
        const dateStr = new Date().toISOString().split('T')[0];

        try {
            const dirPath = path.join(KNOWLEDGE_PATH, type, resourceName);

            if (!fs.existsSync(dirPath)) {
                fs.mkdirSync(dirPath, { recursive: true });
            }

            const filePath = path.join(dirPath, `summary_${dateStr}.md`);
            fs.writeFileSync(filePath, content, 'utf8');
            console.log(`📚 Saved summary artifact: ${filePath}`);
        } catch (error) {
            console.error(`Failed to save knowledge artifact`, error);
        }
    }
}
