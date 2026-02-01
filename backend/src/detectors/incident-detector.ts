import * as cron from 'node-cron';
import { prisma } from '../db/client.js';
import { agentOrchestrator } from '../agents/orchestrator.js';

const CHECK_INTERVAL_SECONDS = 60;

export class IncidentDetector {
    private cronJob: cron.ScheduledTask | null = null;
    private isRunning = false;

    /**
     * Start the incident detector
     */
    public start() {
        if (this.isRunning) {
            console.log('Incident detector already running');
            return;
        }

        this.isRunning = true;

        console.log(`🕵️ Incident detector started (interval: ${CHECK_INTERVAL_SECONDS}s)`);

        // Run immediately
        this.detect().catch(error => console.error('Incident detection failed:', error));

        // Schedule recurring checks
        this.cronJob = cron.schedule(`*/${CHECK_INTERVAL_SECONDS} * * * * *`, () => {
            this.detect().catch(error => console.error('Incident detection failed:', error));
        });
    }

    /**
     * Stop the detector
     */
    public stop() {
        if (this.cronJob) {
            this.cronJob.stop();
            this.cronJob = null;
        }
        this.isRunning = false;
        console.log('🛑 Incident detector stopped');
    }

    /**
     * Main detection loop
     */
    private async detect() {
        await this.detectDockerCrashes();
    }

    /**
     * Rule: Docker Container Crash
     * Condition: state == 'exited' && exitCode != 0
     */
    private async detectDockerCrashes() {
        // 1. Get Docker container facts from the last 10 minutes to verify active monitoring
        //    (We assume FactCollector is running)
        const recentTime = new Date(Date.now() - 10 * 60 * 1000);

        // Find all resources we have data for
        const recentFacts = await prisma.fact.groupBy({
            by: ['resourceRef'],
            where: {
                factType: 'docker_container_status',
                timestamp: { gte: recentTime }
            },
        });

        for (const { resourceRef } of recentFacts) {
            // Get the absolute latest status for this resource
            const fact = await prisma.fact.findFirst({
                where: { resourceRef, factType: 'docker_container_status' },
                orderBy: { timestamp: 'desc' }
            });

            if (!fact) continue;

            const status = fact.value as any;

            // Check for crash condition
            // Note: exitCode might be missing for old facts, but we added it
            if (status.state === 'exited' && status.exitCode !== undefined && status.exitCode !== 0) {
                await this.createIncident(
                    resourceRef,
                    'high', // Crashing container is usually high priority
                    `Container ${status.name} crashed`,
                    `The container **${status.name}** (${status.image}) exited unexpectedly with exit code **${status.exitCode}**.\n\nTime of detection: ${new Date().toLocaleString()}`,
                    ['docker_crash']
                );
            }
        }
    }

    /**
     * Create an incident if one doesn't already exist for this resource
     */
    private async createIncident(
        resourceRef: string,
        severity: string,
        summary: string,
        detail: string,
        symptoms: string[]
    ) {
        // Check for existing OPEN incident for this resource
        // Since affectedResources is JSON, we fetch open incidents and filter in memory
        const openIncidents = await prisma.incident.findMany({
            where: {
                status: { not: 'resolved' }
            }
        });

        const alreadyOpen = openIncidents.some(inc => {
            const affected = inc.affectedResources as string[];
            return Array.isArray(affected) && affected.includes(resourceRef);
        });

        if (alreadyOpen) return;

        console.log(`🚨 [IncidentDetector] Generating Incident: ${summary} (${resourceRef})`);

        try {
            const incident = await prisma.incident.create({
                data: {
                    severity,
                    status: 'open',
                    affectedResources: [resourceRef],
                    symptoms,
                    detectedAt: new Date(),
                    narrative: {
                        create: {
                            timeRange: { start: new Date(), end: new Date() },
                            narrativeText: `## ${summary}\n\n${detail}\n\n*🤖 Autonomous Agents are analyzing this incident...*`,
                            rootCauseHypothesis: 'Pending Analysis',
                            evidenceRefs: [],
                            resolutionSteps: []
                        }
                    }
                }
            });

            // Trigger Agent Orchestration asynchronously
            agentOrchestrator.run(incident.id).catch(err => console.error('Orchestrator failed:', err));

        } catch (error) {
            console.error('Failed to create incident record:', error);
        }
    }
}
