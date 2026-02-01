import { Router } from 'express';
import { ActionExecutor } from '../actions/action-executor.js';

const router = Router();
const executor = new ActionExecutor();

/**
 * POST /api/actions
 * Execute an action on a resource
 */
router.post('/', async (req, res) => {
    try {
        const { actionType, resourceRef, incidentId } = req.body;

        if (!actionType || !resourceRef) {
            return res.status(400).json({ error: 'Missing actionType or resourceRef' });
        }

        const result = await executor.executeAction({
            actionType,
            resourceRef,
            incidentId,
            mode: 'guide'
        });

        res.json(result);
    } catch (error: any) {
        console.error('Action API error:', error);
        res.status(500).json({
            error: 'Failed to execute action',
            details: error.message
        });
    }
});

export const actionRouter = router;
