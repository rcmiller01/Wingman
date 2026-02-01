import { prisma } from '../db/client.js';
import * as dockerAdapter from '../adapters/docker.js';

export interface ActionRequest {
    actionType: 'restart' | 'stop' | 'start';
    resourceRef: string;
    incidentId?: string;
    mode?: 'guide' | 'assist';
}

export class ActionExecutor {
    /**
     * Execute an infrastructure action
     */
    public async executeAction(request: ActionRequest): Promise<any> {
        const { actionType, resourceRef, incidentId, mode = 'guide' } = request;

        console.log(`⚡ Executing action: ${actionType} on ${resourceRef}`);

        // 1. Parse Resource Ref
        let containerId = '';
        if (resourceRef.startsWith('docker://')) {
            containerId = resourceRef.split('docker://')[1];
        } else {
            throw new Error(`Unsupported resource type: ${resourceRef}. Only 'docker://' is supported.`);
        }

        // 2. Create Audit Record
        const actionRecord = await prisma.actionHistory.create({
            data: {
                actionTemplate: actionType,
                targetResource: resourceRef,
                mode,
                status: 'executing',
                approvedBy: 'user', // MVP assumption: triggered by auth'd user
                approvedAt: new Date(),
                executedAt: new Date(),
                incidentId,
                parameters: {}
            }
        });

        try {
            // 3. Execute Action via Adapter
            let result: any = { success: true };

            switch (actionType) {
                case 'restart':
                    await dockerAdapter.restartContainer(containerId);
                    result.message = 'Container restarted successfully';
                    break;
                case 'stop':
                    await dockerAdapter.stopContainer(containerId);
                    result.message = 'Container stopped successfully';
                    break;
                case 'start':
                    await dockerAdapter.startContainer(containerId);
                    result.message = 'Container started successfully';
                    break;
                default:
                    throw new Error(`Unknown action type: ${actionType}`);
            }

            // 4. Update Audit Record (Success)
            await prisma.actionHistory.update({
                where: { id: actionRecord.id },
                data: {
                    status: 'completed',
                    completedAt: new Date(),
                    result
                }
            });

            console.log(`✅ Action completed: ${actionType} on ${resourceRef}`);
            return result;

        } catch (error: any) {
            console.error(`❌ Action execution failed:`, error);

            // 5. Update Audit Record (Failure)
            await prisma.actionHistory.update({
                where: { id: actionRecord.id },
                data: {
                    status: 'failed',
                    completedAt: new Date(),
                    error: error.message || 'Unknown error'
                }
            });

            throw error;
        }
    }
}
