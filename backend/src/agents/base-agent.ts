
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

Instructions:
1. Analyze the conversation history.
2. Provide a clear, professional response.
3. Be concise but thorough.
`;

        const response = await this.callLLM(systemPrompt, history);
        return {
            role: 'assistant',
            name: this.name,
            content: response
        };
    }

    protected async callLLM(systemPrompt: string, history: AgentMessage[]): Promise<string> {
        const LLM_TIMEOUT_MS = 120000; // 2 minutes
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), LLM_TIMEOUT_MS);

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
                }),
                signal: controller.signal
            });

            if (!res.ok) throw new Error(`Ollama chat failed: ${res.statusText}`);

            const data: any = await res.json();
            return data.message.content;
        } catch (error: any) {
            if (error.name === 'AbortError') {
                console.error(`[${this.name}] LLM call timed out after ${LLM_TIMEOUT_MS / 1000}s`);
                return `Analysis timed out. The LLM took too long to respond.`;
            }
            console.error(`[${this.name}] LLM call failed:`, error);
            return "I encountered an error thinking about this.";
        } finally {
            clearTimeout(timeout);
        }
    }
}
