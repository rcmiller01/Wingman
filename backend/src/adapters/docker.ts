import Docker from 'dockerode';
import { Buffer } from 'buffer';
import { config } from '../config/index.js';

// Types for Docker adapter responses
export interface DockerContainerInfo {
    id: string;
    name: string;
    image: string;
    state: string;
    status: string;
    created: Date;
    restartCount: number;
    ports: Array<{ privatePort: number; publicPort?: number; type: string }>;
}

export interface DockerContainerStats {
    cpuPercent: number;
    memoryUsageMb: number;
    memoryLimitMb: number;
    memoryPercent: number;
}

// Initialize Docker client
// Uses DOCKER_HOST env var or defaults to local socket
const docker = new Docker({
    socketPath: process.env.DOCKER_HOST || (process.platform === 'win32'
        ? '//./pipe/docker_engine'
        : '/var/run/docker.sock'),
});

/**
 * List all Docker containers (running and stopped)
 */
export async function listContainers(): Promise<DockerContainerInfo[]> {
    try {
        const containers = await docker.listContainers({ all: true });

        return containers.map((container) => ({
            id: container.Id,
            name: container.Names[0]?.replace(/^\//, '') || 'unknown',
            image: container.Image,
            state: container.State,
            status: container.Status,
            created: new Date(container.Created * 1000),
            restartCount: 0, // Will be populated from inspect
            ports: container.Ports.map((p) => ({
                privatePort: p.PrivatePort,
                publicPort: p.PublicPort,
                type: p.Type,
            })),
        }));
    } catch (error) {
        console.error('Docker adapter: Failed to list containers', error);
        throw error;
    }
}

/**
 * Get detailed info for a specific container
 */
export async function getContainerInfo(containerId: string): Promise<DockerContainerInfo> {
    try {
        const container = docker.getContainer(containerId);
        const info = await container.inspect();

        return {
            id: info.Id,
            name: info.Name.replace(/^\//, ''),
            image: info.Config.Image,
            state: info.State.Status,
            status: info.State.Running ? 'running' : info.State.Status,
            created: new Date(info.Created),
            restartCount: info.RestartCount,
            ports: Object.entries(info.NetworkSettings.Ports || {}).map(([port, bindings]) => {
                const [privatePort, type] = port.split('/');
                return {
                    privatePort: parseInt(privatePort, 10),
                    publicPort: bindings?.[0]?.HostPort ? parseInt(bindings[0].HostPort, 10) : undefined,
                    type: type || 'tcp',
                };
            }),
        };
    } catch (error) {
        console.error(`Docker adapter: Failed to get info for container ${containerId}`, error);
        throw error;
    }
}

/**
 * Get live stats for a container (CPU, memory)
 */
export async function getContainerStats(containerId: string): Promise<DockerContainerStats> {
    try {
        const container = docker.getContainer(containerId);
        const stats = await container.stats({ stream: false });

        // Calculate CPU percentage
        const cpuDelta = stats.cpu_stats.cpu_usage.total_usage - stats.precpu_stats.cpu_usage.total_usage;
        const systemDelta = stats.cpu_stats.system_cpu_usage - stats.precpu_stats.system_cpu_usage;
        const cpuCount = stats.cpu_stats.online_cpus || stats.cpu_stats.cpu_usage.percpu_usage?.length || 1;
        const cpuPercent = systemDelta > 0 ? (cpuDelta / systemDelta) * cpuCount * 100 : 0;

        // Calculate memory
        const memoryUsage = stats.memory_stats.usage || 0;
        const memoryLimit = stats.memory_stats.limit || 1;
        const memoryPercent = (memoryUsage / memoryLimit) * 100;

        return {
            cpuPercent: Math.round(cpuPercent * 100) / 100,
            memoryUsageMb: Math.round(memoryUsage / 1024 / 1024),
            memoryLimitMb: Math.round(memoryLimit / 1024 / 1024),
            memoryPercent: Math.round(memoryPercent * 100) / 100,
        };
    } catch (error) {
        console.error(`Docker adapter: Failed to get stats for container ${containerId}`, error);
        throw error;
    }
}

/**
 * Check if Docker is available
 */
export async function isDockerAvailable(): Promise<boolean> {
    try {
        await docker.ping();
        return true;
    } catch {
        return false;
    }
}

/**
 * Generate a stable resource reference for a Docker container
 */
export function getResourceRef(containerId: string): string {
    return `docker://${containerId.substring(0, 12)}`;
}

export interface LogEntry {
    timestamp: Date;
    stream: 'stdout' | 'stderr';
    message: string;
}

/**
 * Get logs for a container
 */
export async function getContainerLogs(containerId: string, since?: Date): Promise<LogEntry[]> {
    try {
        const container = docker.getContainer(containerId);

        const opts: any = {
            stdout: true,
            stderr: true,
            timestamps: true,
            follow: false,
        };

        if (since) {
            opts.since = Math.floor(since.getTime() / 1000);
        }

        const logsBuffer = await container.logs(opts) as any as Buffer;
        return parseDockerLogs(logsBuffer);
    } catch (error) {
        console.error(`Docker adapter: Failed to get logs for container ${containerId}`, error);
        throw error;
    }
}

/**
 * Parse Docker multiplexed log stream
 * Header: [1 byte stream type] [3 bytes 0] [4 bytes size]
 * Stream types: 0: stdin, 1: stdout, 2: stderr
 */
function parseDockerLogs(buffer: Buffer): LogEntry[] {
    const logs: LogEntry[] = [];
    let offset = 0;

    // Handle case where it's just a string (rare but possible if TTY enabled)
    if (!Buffer.isBuffer(buffer)) {
        // Should check if it's string, but usually types say Buffer. 
        // If string, likely not multiplexed.
        return [];
    }

    while (offset < buffer.length) {
        // Safe check for header
        if (offset + 8 > buffer.length) break;

        const type = buffer[offset];
        const size = buffer.readUInt32BE(offset + 4);
        offset += 8;

        if (offset + size > buffer.length) break;

        const payload = buffer.subarray(offset, offset + size).toString('utf8');
        offset += size;

        // Parse timestamp (RFC3339Nano)
        // Example: 2024-01-01T00:00:00.000000000Z Message content
        const spaceIdx = payload.indexOf(' ');
        if (spaceIdx > 0) {
            const tsString = payload.substring(0, spaceIdx);
            const message = payload.substring(spaceIdx + 1).trim(); // Remove trailing newline

            const timestamp = new Date(tsString);

            if (!isNaN(timestamp.getTime())) {
                logs.push({
                    timestamp,
                    stream: type === 2 ? 'stderr' : 'stdout',
                    message,
                });
            }
        }
    }

    return logs;
}
