import proxmoxApi from 'proxmox-api';
import { config, hasProxmox } from '../config/index.js';

// Types for Proxmox adapter responses
export interface ProxmoxNode {
    node: string;
    status: 'online' | 'offline' | 'unknown';
    cpu: number;
    maxcpu: number;
    mem: number;
    maxmem: number;
    uptime: number;
}

export interface ProxmoxVM {
    vmid: number;
    name: string;
    node: string;
    type: 'qemu' | 'lxc';
    status: 'running' | 'stopped' | 'paused' | 'unknown';
    cpu: number;
    cpus: number;
    mem: number;
    maxmem: number;
    disk: number;
    maxdisk: number;
    uptime: number;
}

// Proxmox client instance (lazy initialized)
let proxmox: ReturnType<typeof proxmoxApi> | null = null;

/**
 * Get or create Proxmox API client
 */
function getClient(): ReturnType<typeof proxmoxApi> {
    if (!proxmox) {
        if (!hasProxmox()) {
            throw new Error('Proxmox is not configured. Please set PROXMOX_HOST, PROXMOX_USER, PROXMOX_TOKEN_NAME, and PROXMOX_TOKEN_VALUE in .env');
        }

        proxmox = proxmoxApi({
            host: config.proxmoxHost!.replace(/^https?:\/\//, '').replace(/:\d+$/, ''),
            port: parseInt(config.proxmoxHost!.match(/:(\d+)$/)?.[1] || '8006', 10),
            tokenID: `${config.proxmoxUser}!${config.proxmoxTokenName}`,
            tokenSecret: config.proxmoxTokenValue!,
            // Ignore self-signed certs if configured
            ...(config.proxmoxVerifySsl === false && {
                // @ts-ignore - proxmox-api supports this but types may not
                ignoreSSL: true
            }),
        });
    }
    return proxmox;
}

/**
 * List all nodes in the Proxmox cluster
 */
export async function listNodes(): Promise<ProxmoxNode[]> {
    try {
        const client = getClient();
        const nodes = await client.nodes.$get();

        return nodes.map((node: any) => ({
            node: node.node,
            status: node.status === 'online' ? 'online' : node.status === 'offline' ? 'offline' : 'unknown',
            cpu: node.cpu || 0,
            maxcpu: node.maxcpu || 1,
            mem: node.mem || 0,
            maxmem: node.maxmem || 1,
            uptime: node.uptime || 0,
        }));
    } catch (error) {
        console.error('Proxmox adapter: Failed to list nodes', error);
        throw error;
    }
}

/**
 * List all VMs (QEMU) on a specific node
 */
export async function listVMs(nodeName: string): Promise<ProxmoxVM[]> {
    try {
        const client = getClient();
        const vms = await client.nodes.$(nodeName).qemu.$get();

        return vms.map((vm: any) => ({
            vmid: vm.vmid,
            name: vm.name || `VM-${vm.vmid}`,
            node: nodeName,
            type: 'qemu' as const,
            status: vm.status === 'running' ? 'running' : vm.status === 'stopped' ? 'stopped' : 'unknown',
            cpu: vm.cpu || 0,
            cpus: vm.cpus || 1,
            mem: vm.mem || 0,
            maxmem: vm.maxmem || 0,
            disk: vm.disk || 0,
            maxdisk: vm.maxdisk || 0,
            uptime: vm.uptime || 0,
        }));
    } catch (error) {
        console.error(`Proxmox adapter: Failed to list VMs on node ${nodeName}`, error);
        throw error;
    }
}

/**
 * List all LXC containers on a specific node
 */
export async function listLXCs(nodeName: string): Promise<ProxmoxVM[]> {
    try {
        const client = getClient();
        const containers = await client.nodes.$(nodeName).lxc.$get();

        return containers.map((lxc: any) => ({
            vmid: lxc.vmid,
            name: lxc.name || `LXC-${lxc.vmid}`,
            node: nodeName,
            type: 'lxc' as const,
            status: lxc.status === 'running' ? 'running' : lxc.status === 'stopped' ? 'stopped' : 'unknown',
            cpu: lxc.cpu || 0,
            cpus: lxc.cpus || 1,
            mem: lxc.mem || 0,
            maxmem: lxc.maxmem || 0,
            disk: lxc.disk || 0,
            maxdisk: lxc.maxdisk || 0,
            uptime: lxc.uptime || 0,
        }));
    } catch (error) {
        console.error(`Proxmox adapter: Failed to list LXCs on node ${nodeName}`, error);
        throw error;
    }
}

/**
 * List all VMs and LXCs across all nodes
 */
export async function listAllResources(): Promise<{ nodes: ProxmoxNode[]; vms: ProxmoxVM[] }> {
    try {
        const nodes = await listNodes();
        const allVMs: ProxmoxVM[] = [];

        for (const node of nodes) {
            if (node.status === 'online') {
                const [vms, lxcs] = await Promise.all([
                    listVMs(node.node),
                    listLXCs(node.node),
                ]);
                allVMs.push(...vms, ...lxcs);
            }
        }

        return { nodes, vms: allVMs };
    } catch (error) {
        console.error('Proxmox adapter: Failed to list all resources', error);
        throw error;
    }
}

/**
 * Check if Proxmox is available
 */
export async function isProxmoxAvailable(): Promise<boolean> {
    if (!hasProxmox()) {
        return false;
    }
    try {
        const client = getClient();
        await client.version.$get();
        return true;
    } catch {
        return false;
    }
}

/**
 * Generate a stable resource reference for a Proxmox resource
 */
export function getResourceRef(node: string, vmid: number, type: 'qemu' | 'lxc'): string {
    return `proxmox://${node}/${type}/${vmid}`;
}

/**
 * Generate a stable resource reference for a Proxmox node
 */
export function getNodeResourceRef(node: string): string {
    return `proxmox://${node}`;
}
