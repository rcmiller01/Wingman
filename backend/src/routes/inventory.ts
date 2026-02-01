import { Router, Request, Response } from 'express';
import { prisma } from '../db/client.js';
import * as dockerAdapter from '../adapters/docker.js';
import * as proxmoxAdapter from '../adapters/proxmox.js';
import { hasProxmox } from '../config/index.js';
import { getCollectorStatus } from '../collectors/fact-collector.js';

const router = Router();

/**
 * GET /api/inventory
 * Returns aggregated inventory from all sources
 */
router.get('/', async (_req: Request, res: Response) => {
    try {
        const inventory: {
            docker: { available: boolean; containers: any[] };
            proxmox: { available: boolean; configured: boolean; nodes: any[]; vms: any[] };
            collector: { running: boolean; intervalSeconds: number };
        } = {
            docker: { available: false, containers: [] },
            proxmox: { available: false, configured: hasProxmox(), nodes: [], vms: [] },
            collector: getCollectorStatus(),
        };

        // Get Docker inventory
        try {
            if (await dockerAdapter.isDockerAvailable()) {
                inventory.docker.available = true;
                inventory.docker.containers = await dockerAdapter.listContainers();
            }
        } catch (error) {
            console.error('Inventory route: Docker unavailable', error);
        }

        // Get Proxmox inventory
        try {
            if (hasProxmox() && await proxmoxAdapter.isProxmoxAvailable()) {
                inventory.proxmox.available = true;
                const { nodes, vms } = await proxmoxAdapter.listAllResources();
                inventory.proxmox.nodes = nodes;
                inventory.proxmox.vms = vms;
            }
        } catch (error) {
            console.error('Inventory route: Proxmox unavailable', error);
        }

        res.json(inventory);
    } catch (error) {
        console.error('Inventory route error:', error);
        res.status(500).json({ error: 'Failed to fetch inventory' });
    }
});

/**
 * GET /api/inventory/docker
 * Returns Docker containers
 */
router.get('/docker', async (_req: Request, res: Response) => {
    try {
        const available = await dockerAdapter.isDockerAvailable();
        if (!available) {
            return res.json({ available: false, containers: [] });
        }

        const containers = await dockerAdapter.listContainers();

        // Enrich with stats for running containers
        const enriched = await Promise.all(
            containers.map(async (container) => {
                if (container.state === 'running') {
                    try {
                        const stats = await dockerAdapter.getContainerStats(container.id);
                        return { ...container, stats };
                    } catch {
                        return container;
                    }
                }
                return container;
            })
        );

        res.json({ available: true, containers: enriched });
    } catch (error) {
        console.error('Docker inventory error:', error);
        res.status(500).json({ error: 'Failed to fetch Docker inventory' });
    }
});

/**
 * GET /api/inventory/docker/:id
 * Returns specific Docker container details
 */
router.get('/docker/:id', async (req: Request, res: Response) => {
    try {
        const { id } = req.params;
        const available = await dockerAdapter.isDockerAvailable();

        if (!available) {
            return res.status(503).json({ error: 'Docker service unavailable' });
        }

        const info = await dockerAdapter.getContainerInfo(id);

        let stats = null;
        if (info.state === 'running') {
            try {
                stats = await dockerAdapter.getContainerStats(id);
            } catch { /* ignore stats failure */ }
        }

        res.json({ ...info, stats });
    } catch (error) {
        console.error(`Docker container ${req.params.id} error:`, error);
        res.status(404).json({ error: 'Container not found' });
    }
});

/**
 * GET /api/inventory/proxmox
 * Returns Proxmox nodes, VMs, and LXCs
 */
router.get('/proxmox', async (_req: Request, res: Response) => {
    try {
        if (!hasProxmox()) {
            return res.json({
                configured: false,
                available: false,
                nodes: [],
                vms: [],
                message: 'Proxmox not configured. Set PROXMOX_HOST, PROXMOX_USER, PROXMOX_TOKEN_NAME, PROXMOX_TOKEN_VALUE in .env'
            });
        }

        const available = await proxmoxAdapter.isProxmoxAvailable();
        if (!available) {
            return res.json({ configured: true, available: false, nodes: [], vms: [] });
        }

        const { nodes, vms } = await proxmoxAdapter.listAllResources();
        res.json({ configured: true, available: true, nodes, vms });
    } catch (error) {
        console.error('Proxmox inventory error:', error);
        res.status(500).json({ error: 'Failed to fetch Proxmox inventory' });
    }
});

/**
 * GET /api/inventory/facts
 * Returns historical facts, optionally filtered by resourceRef
 */
router.get('/facts', async (req: Request, res: Response) => {
    try {
        const { resourceRef, factType, limit = '50' } = req.query;

        const where: any = {};
        if (resourceRef) where.resourceRef = resourceRef as string;
        if (factType) where.factType = factType as string;

        const facts = await prisma.fact.findMany({
            where,
            orderBy: { createdAt: 'desc' },
            take: Math.min(parseInt(limit as string, 10), 100),
        });

        res.json({ facts, count: facts.length });
    } catch (error) {
        console.error('Facts query error:', error);
        res.status(500).json({ error: 'Failed to fetch facts' });
    }
});

/**
 * GET /api/inventory/stats
 * Returns summary statistics
 */
router.get('/stats', async (_req: Request, res: Response) => {
    try {
        const stats = {
            docker: { total: 0, running: 0, stopped: 0 },
            proxmox: { nodes: 0, vms: 0, lxcs: 0, running: 0 },
            facts: { total: 0, last24h: 0 },
        };

        // Docker stats
        try {
            if (await dockerAdapter.isDockerAvailable()) {
                const containers = await dockerAdapter.listContainers();
                stats.docker.total = containers.length;
                stats.docker.running = containers.filter(c => c.state === 'running').length;
                stats.docker.stopped = containers.filter(c => c.state !== 'running').length;
            }
        } catch { }

        // Proxmox stats
        try {
            if (hasProxmox() && await proxmoxAdapter.isProxmoxAvailable()) {
                const { nodes, vms } = await proxmoxAdapter.listAllResources();
                stats.proxmox.nodes = nodes.length;
                stats.proxmox.vms = vms.filter(v => v.type === 'qemu').length;
                stats.proxmox.lxcs = vms.filter(v => v.type === 'lxc').length;
                stats.proxmox.running = vms.filter(v => v.status === 'running').length;
            }
        } catch { }

        // Fact stats
        try {
            stats.facts.total = await prisma.fact.count();
            stats.facts.last24h = await prisma.fact.count({
                where: {
                    createdAt: { gte: new Date(Date.now() - 24 * 60 * 60 * 1000) },
                },
            });
        } catch { }

        res.json(stats);
    } catch (error) {
        console.error('Stats error:', error);
        res.status(500).json({ error: 'Failed to fetch stats' });
    }
});

export default router;
