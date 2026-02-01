import { Router, Request, Response } from 'express';
import { prisma } from '../db/client.js';

export const incidentRouter = Router();

/**
 * GET /api/incidents
 * List incidents with pagination and filtering
 */
incidentRouter.get('/', async (req: Request, res: Response) => {
    try {
        const { status = 'open', limit = '50', offset = '0' } = req.query;

        const where: any = {};
        if (status !== 'all') {
            where.status = status;
        }

        const [incidents, total] = await Promise.all([
            prisma.incident.findMany({
                where,
                orderBy: { detectedAt: 'desc' },
                take: parseInt(limit as string),
                skip: parseInt(offset as string),
            }),
            prisma.incident.count({ where })
        ]);

        res.json({
            data: incidents,
            pagination: {
                limit: parseInt(limit as string),
                offset: parseInt(offset as string),
                total
            }
        });
    } catch (error) {
        console.error('Failed to list incidents:', error);
        res.status(500).json({ error: 'Failed to list incidents' });
    }
});

/**
 * GET /api/incidents/:id
 * Get incident details with narrative and action history
 */
incidentRouter.get('/:id', async (req: Request, res: Response) => {
    try {
        const { id } = req.params;
        const incident = await prisma.incident.findUnique({
            where: { id },
            include: {
                narrative: true,
                actions: {
                    orderBy: { createdAt: 'desc' }
                }
            }
        });

        if (!incident) {
            return res.status(404).json({ error: 'Incident not found' });
        }

        res.json(incident);
    } catch (error) {
        console.error('Failed to get incident:', error);
        res.status(500).json({ error: 'Failed to get incident' });
    }
});
