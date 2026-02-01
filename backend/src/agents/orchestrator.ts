
import { prisma } from '../db/client.js';
import { AnalystAgent } from './specialized/analyst.js';
import { OperatorAgent } from './specialized/operator.js';

export class AgentOrchestrator {
    private analyst = new AnalystAgent();
    private operator = new OperatorAgent();

    /**
     * Run the multi-agent collaboration loop for an incident
     */
    async run(incidentId: string) {
        console.log(`[Orchestrator] Activating agents for Incident ${incidentId}`);

        const incident = await prisma.incident.findUnique({
            where: { id: incidentId },
            include: { narrative: true }
        });

        if (!incident || !incident.narrative) {
            console.error('[Orchestrator] Incident or narrative not found');
            return;
        }

        const resourceRef = (incident.affectedResources as string[])[0] || "unknown";
        const summary = incident.narrative.narrativeText; // Initial details

        let diagnosis = "Analysis could not be completed.";
        let actionPlan = "No recommendations available.";

        // 1. Analyst Phase
        try {
            console.log(`[Orchestrator] Phase 1: Analyst Diagnosis`);
            diagnosis = await this.analyst.analyze(summary, `Resource: ${resourceRef}`);
        } catch (err) {
            console.error('[Orchestrator] Analyst phase failed:', err);
            diagnosis = "The Analyst encountered an error during analysis.";
        }

        // 2. Operator Phase
        try {
            console.log(`[Orchestrator] Phase 2: Operator Action Plan`);
            actionPlan = await this.operator.proposeAction(diagnosis, resourceRef);
        } catch (err) {
            console.error('[Orchestrator] Operator phase failed:', err);
            actionPlan = "The Operator could not generate recommendations.";
        }

        // 3. Synthesis & Storage
        const trace = [
            { agent: 'Analyst', content: diagnosis },
            { agent: 'Operator', content: actionPlan }
        ];

        // Extract a short root cause hypothesis (first line or first sentence)
        const rootCauseHypothesis = this.extractRootCause(diagnosis);

        // Combine into a final narrative
        const finalNarrative = `
## Multi-Agent Analysis

### Analyst Report
${diagnosis}

### Operator Recommendations
${actionPlan}

---
## Original Detection
${summary}
`;

        // Update Database
        try {
            await prisma.incidentNarrative.update({
                where: { id: incident.narrative.id },
                data: {
                    narrativeText: finalNarrative,
                    agentTrace: trace,
                    rootCauseHypothesis
                }
            });
            console.log(`[Orchestrator] Workflow complete for Incident ${incidentId}`);
        } catch (err) {
            console.error('[Orchestrator] Failed to update narrative:', err);
        }
    }

    /**
     * Extract a short root cause hypothesis from the analyst's full diagnosis
     */
    private extractRootCause(diagnosis: string): string {
        if (!diagnosis || diagnosis.length < 10) return "Unknown";

        // Try to find a line starting with "Root Cause:" or similar
        const lines = diagnosis.split('\n');
        for (const line of lines) {
            const lower = line.toLowerCase();
            if (lower.includes('root cause') || lower.includes('hypothesis')) {
                return line.replace(/^[#*\-\s]+/, '').trim().substring(0, 200);
            }
        }

        // Fallback: return first meaningful line
        const firstLine = lines.find(l => l.trim().length > 20) || diagnosis.substring(0, 200);
        return firstLine.trim().substring(0, 200);
    }
}

export const agentOrchestrator = new AgentOrchestrator();
