import { Router } from 'express';
import { prisma } from '../db/client.js';

export const logRouter = Router();

// GET /api/logs
logRouter.get('/', async (req, res) => {
    try {
        const { resourceRef, limit = '100', offset = '0' } = req.query;

        if (!resourceRef) {
            return res.status(400).json({ error: 'resourceRef is required' });
        }

        const logs = await prisma.log.findMany({
            where: {
                resourceRef: String(resourceRef),
            },
            orderBy: {
                timestamp: 'desc',
            },
            take: Number(limit),
            skip: Number(offset),
        });

        const total = await prisma.log.count({
            where: {
                resourceRef: String(resourceRef),
            },
        });

        res.json({
            data: logs,
            pagination: {
                total,
                limit: Number(limit),
                offset: Number(offset),
            }
        });
    } catch (error) {
        console.error('Failed to fetch logs:', error);
        res.status(500).json({ error: 'Internal server error' });
    }
});
