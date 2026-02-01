
import { BaseAgent, AgentMessage } from '../base-agent.js';
import { contextProvider } from '../../memory/context-provider.js';

export class AnalystAgent extends BaseAgent {
    public name = "Analyst";
    public role = "System Investigator";
    public goal = "Analyze incidents to determine root cause using logs and historical memory.";

    async analyze(incidentSummary: string, incidentDetail: string): Promise<string> {
        // 1. Gather Context
        console.log(`[Analyst] Gathering intelligence for: ${incidentSummary}`);
        const contextItems = await contextProvider.getContext(`${incidentSummary} ${incidentDetail}`, 5);
        const contextStr = contextProvider.formatContext(contextItems);

        // 2. Formulate thought process
        const history: AgentMessage[] = [
            {
                role: 'user',
                content: `Here is a new incident report:\nSummary: ${incidentSummary}\nDetail: ${incidentDetail}\n\nHistorical Context:\n${contextStr}\n\nPlease provide a detailed analysis and root cause hypothesis.`
            }
        ];

        // 3. Think
        const response = await this.chat(history);
        return response.content;
    }
}
