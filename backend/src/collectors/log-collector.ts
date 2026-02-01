import cron from 'node-cron';
import { prisma } from '../db/client.js';
import * as dockerAdapter from '../adapters/docker.js';
import { LogAnalyzer } from '../analysis/log-analyzer.js';

export class LogCollector {
    private analyzer = new LogAnalyzer();
    private isRunning = false;

    constructor() {
        console.log('Initializing Log Collector (scheduled every 30s)');
        // Run every 30 seconds
        cron.schedule('*/30 * * * * *', () => this.collect());
    }

    async collect() {
        if (this.isRunning) return;
        this.isRunning = true;

        try {
            // Only proceed if Docker is available
            if (!await dockerAdapter.isDockerAvailable()) {
                // Silent return or debug log
                return;
            }

            const containers = await dockerAdapter.listContainers();
            const retentionDate = new Date();
            retentionDate.setDate(retentionDate.getDate() + 90); // 90 days retention

            for (const container of containers) {
                // Only collect for running containers
                if (container.state !== 'running') continue;

                const resourceRef = dockerAdapter.getResourceRef(container.id);

                // Get last log timestamp from DB to determine 'since'
                const lastLog = await prisma.log.findFirst({
                    where: { resourceRef },
                    orderBy: { timestamp: 'desc' },
                });

                // Add 1 second to last timestamp to avoid duplicates (Docker API resolution is seconds usually)
                // If we use milliseconds, we might still get duplicates if Docker rounds down.
                let since: Date | undefined;
                if (lastLog) {
                    since = new Date(lastLog.timestamp.getTime() + 1000);
                }

                // Fetch logs
                const logs = await dockerAdapter.getContainerLogs(container.id, since);

                if (logs.length === 0) continue;

                console.log(`[LogCollector] Found ${logs.length} new logs for ${container.name}`);

                // Store logs in batches
                await prisma.log.createMany({
                    data: logs.map(l => ({
                        resourceRef,
                        logSource: l.stream,
                        content: l.message,
                        timestamp: l.timestamp,
                        level: l.stream === 'stderr' ? 'error' : 'info', // Basic heuristic
                        retentionDate,
                    }))
                });

                // Analyze for errors
                const errors = this.analyzer.analyze(logs);

                if (errors.length > 0) {
                    console.log(`[LogCollector] Detected ${errors.length} error signatures in ${container.name}`);
                    await prisma.fact.createMany({
                        data: errors.map(e => ({
                            resourceRef,
                            factType: 'error_signature',
                            value: { signature: e.signature, message: e.fullMessage },
                            timestamp: e.timestamp,
                            source: 'log_collector',
                        }))
                    });
                }
            }
        } catch (error) {
            console.error('Error in LogCollector:', error);
        } finally {
            this.isRunning = false;
        }
    }
}
