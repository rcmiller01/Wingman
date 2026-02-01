
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
        console.log(`🤖 [Orchestrator] Activating agents for Incident ${incidentId}`);

        const incident = await prisma.incident.findUnique({
            where: { id: incidentId },
            include: { narrative: true }
        });

        if (!incident || !incident.narrative) {
            console.error('Incident or narrative not found');
            return;
        }

        const resourceRef = (incident.affectedResources as string[])[0] || "unknown";
        const summary = incident.narrative.narrativeText; // Initial details

        // 1. Analyst Phase
        console.log(`🤖 [Orchestrator] Phase 1: Analyst Diagnosis`);
        const diagnosis = await this.analyst.analyze(summary, `Resource: ${resourceRef}`);

        // 2. Operator Phase
        console.log(`🤖 [Orchestrator] Phase 2: Operator Action Plan`);
        const actionPlan = await this.operator.proposeAction(diagnosis, resourceRef);

        // 3. Synthesis & Storage
        const trace = [
            { agent: 'Analyst', content: diagnosis },
            { agent: 'Operator', content: actionPlan }
        ];

        // Combine into a final narrative
        const finalNarrative = `
## 🤖 Multi-Agent Analysis

### 🕵️ Analyst Report
${diagnosis}

### 🛠️ Operator Recommendations
${actionPlan}

---
## Original Detection
${summary}
`;

        // Update Database
        await prisma.incidentNarrative.update({
            where: { id: incident.narrative.id },
            data: {
                narrativeText: finalNarrative,
                agentTrace: trace,
                rootCauseHypothesis: "See Analyst Report"
            }
        });

        console.log(`🤖 [Orchestrator] Workflow identification complete.`);
    }
}

export const agentOrchestrator = new AgentOrchestrator();
