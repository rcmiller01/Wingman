
import { config } from '../config/index.js';

export interface AgentMessage {
    role: 'user' | 'assistant' | 'system';
    content: string;
    name?: string; // e.g., "Analyst", "Operator"
}

export interface AgentTool {
    name: string;
    description: string;
    execute: (params: any) => Promise<any>;
}

export abstract class BaseAgent {
    public abstract name: string;
    public abstract role: string;
    public abstract goal: string;

    protected tools: AgentTool[] = [];

    /**
     * Core thinking loop.
     * Takes conversation history, returns a response.
     */
    async chat(history: AgentMessage[]): Promise<AgentMessage> {
        // Construct system prompt
        const systemPrompt = `You are ${this.name}, a ${this.role}.
Goal: ${this.goal}

Available Tools:
${this.tools.map(t => `- ${t.name}: ${t.description}`).join('\n')}

Instructions:
1. Analyze the conversation history.
2. If you need to use a tool, output JSON: {"tool": "name", "params": {...}}
3. If you have a final answer or response, just speak normally.
4. Be concise and professional.
`;

        const response = await this.callLLM(systemPrompt, history);
        return {
            role: 'assistant',
            name: this.name,
            content: response
        };
    }

    protected async callLLM(systemPrompt: string, history: AgentMessage[]): Promise<string> {
        try {
            // Convert history to Ollama format
            const messages = [
                { role: 'system', content: systemPrompt },
                ...history.map(m => ({ role: m.role, content: m.name ? `${m.name}: ${m.content}` : m.content }))
            ];

            const res = await fetch(`${config.ollamaHost}/api/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model: config.ollamaModel,
                    messages: messages,
                    stream: false
                })
            });

            if (!res.ok) throw new Error(`Ollama chat failed: ${res.statusText}`);

            const data: any = await res.json();
            return data.message.content;
        } catch (error) {
            console.error(`[${this.name}] LLM call failed:`, error);
            return "I encountered an error thinking about this.";
        }
    }
}
