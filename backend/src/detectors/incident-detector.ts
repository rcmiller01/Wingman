import * as cron from 'node-cron';
import { prisma } from '../db/client.js';
import { contextProvider } from '../memory/context-provider.js';
import { config } from '../config/index.js';

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

        // Generate AI analysis with RAG
        const analysis = await this.generateAIAnalysis(summary, detail, resourceRef);

        try {
            await prisma.incident.create({
                data: {
                    severity,
                    status: 'open',
                    affectedResources: [resourceRef],
                    symptoms,
                    detectedAt: new Date(),
                    narrative: {
                        create: {
                            timeRange: { start: new Date(), end: new Date() },
                            narrativeText: analysis.narrative,
                            rootCauseHypothesis: analysis.rootCause,
                            evidenceRefs: [],
                            resolutionSteps: []
                        }
                    }
                }
            });
        } catch (error) {
            console.error('Failed to create incident record:', error);
        }
    }

    /**
     * Use LLM + RAG to generate a better narrative
     */
    private async generateAIAnalysis(summary: string, detail: string, resourceRef: string): Promise<{ narrative: string, rootCause: string }> {
        try {
            // 1. Get Context
            const contextItems = await contextProvider.getContext(`${summary} ${detail}`, 3);
            const contextStr = contextProvider.formatContext(contextItems);

            // 2. Prompt
            const prompt = `You are a Site Reliability Engineer (SRE) AI.
Analyze the following incident and provide a professional Incident Narrative and a Root Cause Hypothesis.
Use the provided historical context if relevant to identify patterns (e.g., if this container has crashed before).

## Current Incident
Resource: ${resourceRef}
Summary: ${summary}
Detail: ${detail}

## Historical Context (Previous Logs/Memories)
${contextStr || "No relevant history found."}

## Instructions
1. Write a clear, markdown-formatted "Narrative" describing what happened. Mention if this is a recurring issue based on context.
2. Provide a "Root Cause Hypothesis".

Format your response as JSON:
{
  "narrative": "markdown string...",
  "rootCause": "short string..."
}`;

            // 3. Call Ollama
            const response = await fetch(`${config.ollamaHost}/api/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model: config.ollamaModel, // e.g., qwen2.5:7b
                    prompt: prompt,
                    stream: false,
                    format: 'json' // Enforce JSON output
                })
            });

            if (!response.ok) throw new Error(`Ollama failed: ${response.statusText}`);

            const data: any = await response.json();
            const result = JSON.parse(data.response);

            return {
                narrative: result.narrative || `## ${summary}\n\n${detail}`,
                rootCause: result.rootCause || 'Unknown process failure'
            };

        } catch (error) {
            console.error('Failed to generate AI analysis, falling back to basic details:', error);
            // Fallback
            return {
                narrative: `## ${summary}\n\n${detail}\n\n*(AI Analysis Unavailable)*`,
                rootCause: 'Process crash or configuration error (Fallback)'
            };
        }
    }
}
