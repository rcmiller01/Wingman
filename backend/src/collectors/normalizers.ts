import { Prisma } from '@prisma/client';
import { DockerContainerInfo, DockerContainerStats, getResourceRef as getDockerRef } from '../adapters/docker.js';
import { ProxmoxNode, ProxmoxVM, getResourceRef as getProxmoxRef, getNodeResourceRef } from '../adapters/proxmox.js';

// Fact types for different kinds of observations
export type FactType =
    | 'docker_container_status'
    | 'docker_container_stats'
    | 'proxmox_node_status'
    | 'proxmox_vm_status'
    | 'proxmox_lxc_status';

export interface NormalizedFact {
    resourceRef: string;
    factType: FactType;
    value: Prisma.InputJsonValue;
    source: string;
}

/**
 * Normalize a Docker container to a Fact
 */
export function normalizeDockerContainer(container: DockerContainerInfo): NormalizedFact {
    return {
        resourceRef: getDockerRef(container.id),
        factType: 'docker_container_status',
        value: {
            id: container.id,
            name: container.name,
            image: container.image,
            state: container.state,
            status: container.status,
            created: container.created.toISOString(),
            restartCount: container.restartCount,
            ports: container.ports,
        },
        source: 'docker_adapter',
    };
}

/**
 * Normalize Docker container stats to a Fact
 */
export function normalizeDockerStats(containerId: string, stats: DockerContainerStats): NormalizedFact {
    return {
        resourceRef: getDockerRef(containerId),
        factType: 'docker_container_stats',
        value: {
            cpuPercent: stats.cpuPercent,
            memoryUsageMb: stats.memoryUsageMb,
            memoryLimitMb: stats.memoryLimitMb,
            memoryPercent: stats.memoryPercent,
        },
        source: 'docker_adapter',
    };
}

/**
 * Normalize a Proxmox node to a Fact
 */
export function normalizeProxmoxNode(node: ProxmoxNode): NormalizedFact {
    return {
        resourceRef: getNodeResourceRef(node.node),
        factType: 'proxmox_node_status',
        value: {
            node: node.node,
            status: node.status,
            cpuUsage: node.maxcpu > 0 ? (node.cpu / node.maxcpu) * 100 : 0,
            cpuCores: node.maxcpu,
            memoryUsedMb: Math.round(node.mem / 1024 / 1024),
            memoryTotalMb: Math.round(node.maxmem / 1024 / 1024),
            memoryPercent: node.maxmem > 0 ? (node.mem / node.maxmem) * 100 : 0,
            uptimeSeconds: node.uptime,
        },
        source: 'proxmox_adapter',
    };
}

/**
 * Normalize a Proxmox VM to a Fact
 */
export function normalizeProxmoxVM(vm: ProxmoxVM): NormalizedFact {
    const factType: FactType = vm.type === 'lxc' ? 'proxmox_lxc_status' : 'proxmox_vm_status';

    return {
        resourceRef: getProxmoxRef(vm.node, vm.vmid, vm.type),
        factType,
        value: {
            vmid: vm.vmid,
            name: vm.name,
            node: vm.node,
            type: vm.type,
            status: vm.status,
            cpuUsage: vm.cpus > 0 ? (vm.cpu / vm.cpus) * 100 : 0,
            cpuCores: vm.cpus,
            memoryUsedMb: Math.round(vm.mem / 1024 / 1024),
            memoryTotalMb: Math.round(vm.maxmem / 1024 / 1024),
            memoryPercent: vm.maxmem > 0 ? (vm.mem / vm.maxmem) * 100 : 0,
            diskUsedGb: Math.round(vm.disk / 1024 / 1024 / 1024),
            diskTotalGb: Math.round(vm.maxdisk / 1024 / 1024 / 1024),
            uptimeSeconds: vm.uptime,
        },
        source: 'proxmox_adapter',
    };
}
