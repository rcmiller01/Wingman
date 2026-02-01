
import { BaseAgent, AgentMessage } from '../base-agent.js';

export class OperatorAgent extends BaseAgent {
    public name = "Operator";
    public role = "Site Reliability Engineer";
    public goal = "Propose safe and effective remediation actions based on the analysis.";

    async proposeAction(analysis: string, affectedResource: string): Promise<string> {
        const history: AgentMessage[] = [
            {
                role: 'user',
                content: `The Analyst has provided this diagnosis:\n${analysis}\n\nThe affected resource is: ${affectedResource}\n\nWhat immediate actions do you recommend? List them clearly.`
            }
        ];

        const response = await this.chat(history);
        return response.content;
    }
}
