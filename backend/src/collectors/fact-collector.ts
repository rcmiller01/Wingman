import * as cron from 'node-cron';
import { prisma } from '../db/client.js';
import * as dockerAdapter from '../adapters/docker.js';
import * as proxmoxAdapter from '../adapters/proxmox.js';
import {
    normalizeDockerContainer,
    normalizeDockerStats,
    normalizeProxmoxNode,
    normalizeProxmoxVM,
    NormalizedFact
} from './normalizers.js';
import { hasProxmox } from '../config/index.js';

// Collection interval in seconds (default: 30s)

// Collection interval in seconds (default: 30s)
const COLLECTION_INTERVAL_SECONDS = parseInt(process.env.FACT_COLLECTION_INTERVAL || '30', 10);

// Track if collector is running
let isRunning = false;
let cronJob: ReturnType<typeof cron.schedule> | null = null;

/**
 * Collect facts from all adapters and store in database
 */
export async function collectFacts(): Promise<{ docker: number; proxmox: number }> {
    const results = { docker: 0, proxmox: 0 };
    const factsToStore: NormalizedFact[] = [];

    // Collect Docker facts
    try {
        if (await dockerAdapter.isDockerAvailable()) {
            const containers = await dockerAdapter.listContainers();

            for (const container of containers) {
                // Get detailed info with restart count
                try {
                    const info = await dockerAdapter.getContainerInfo(container.id);
                    factsToStore.push(normalizeDockerContainer(info));

                    // Only get stats for running containers
                    if (info.state === 'running') {
                        try {
                            const stats = await dockerAdapter.getContainerStats(container.id);
                            factsToStore.push(normalizeDockerStats(container.id, stats));
                        } catch (statsError) {
                            // Stats may fail for some containers, continue
                        }
                    }
                    results.docker++;
                } catch (infoError) {
                    // Use basic container info if inspect fails
                    factsToStore.push(normalizeDockerContainer(container));
                    results.docker++;
                }
            }
            console.log(`📦 Collected ${results.docker} Docker container facts`);
        }
    } catch (error) {
        console.error('Fact collector: Docker collection failed', error);
    }

    // Collect Proxmox facts
    try {
        if (hasProxmox() && await proxmoxAdapter.isProxmoxAvailable()) {
            const { nodes, vms } = await proxmoxAdapter.listAllResources();

            // Store node facts
            for (const node of nodes) {
                factsToStore.push(normalizeProxmoxNode(node));
                results.proxmox++;
            }

            // Store VM/LXC facts
            for (const vm of vms) {
                factsToStore.push(normalizeProxmoxVM(vm));
                results.proxmox++;
            }
            console.log(`🖥️ Collected ${results.proxmox} Proxmox facts (${nodes.length} nodes, ${vms.length} VMs/LXCs)`);
        }
    } catch (error) {
        console.error('Fact collector: Proxmox collection failed', error);
    }

    // Store all facts in database
    if (factsToStore.length > 0) {
        try {
            await prisma.fact.createMany({
                data: factsToStore.map((fact) => ({
                    resourceRef: fact.resourceRef,
                    factType: fact.factType,
                    value: fact.value,
                    source: fact.source,
                })),
            });
            console.log(`💾 Stored ${factsToStore.length} facts in database`);
        } catch (error) {
            console.error('Fact collector: Failed to store facts', error);
        }
    }

    return results;
}

/**
 * Start the fact collector scheduler
 */
export function startCollector(): void {
    if (isRunning) {
        console.log('Fact collector already running');
        return;
    }

    // Run immediately on startup
    console.log(`🚀 Starting fact collector (interval: ${COLLECTION_INTERVAL_SECONDS}s)`);
    collectFacts().catch(console.error);

    // Schedule recurring collection
    const cronExpression = `*/${COLLECTION_INTERVAL_SECONDS} * * * * *`;
    cronJob = cron.schedule(cronExpression, () => {
        collectFacts().catch(console.error);
    });

    isRunning = true;
}

/**
 * Stop the fact collector scheduler
 */
export function stopCollector(): void {
    if (cronJob) {
        cronJob.stop();
        cronJob = null;
    }
    isRunning = false;
    console.log('🛑 Fact collector stopped');
}

/**
 * Get collector status
 */
export function getCollectorStatus(): { running: boolean; intervalSeconds: number } {
    return {
        running: isRunning,
        intervalSeconds: COLLECTION_INTERVAL_SECONDS,
    };
}
