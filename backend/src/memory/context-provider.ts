
import { qdrantService } from './qdrant-client.js';

interface ContextItem {
    source: string;
    content: string;
    relevance: number;
    timestamp: string;
}

export class ContextProvider {
    /**
     * Retrieve relevant context for a given query (e.g. incident description)
     */
    async getContext(query: string, limit: number = 5): Promise<ContextItem[]> {
        console.log(`[ContextProvider] Searching for: "${query.substring(0, 50)}..."`);

        try {
            const results = await qdrantService.search(query, limit);

            if (results.length === 0) {
                console.log('[ContextProvider] No relevant context found in memory');
            }

            return results.map(hit => ({
                source: `Memory (${hit.payload.resourceRef})`,
                content: hit.payload.content,
                relevance: hit.score,
                timestamp: hit.payload.timestamp
            }));
        } catch (error) {
            console.error('[ContextProvider] Failed to get context:', error);
            return [];
        }
    }

    /**
     * Format context as a string for LLM injection
     */
    formatContext(items: ContextItem[]): string {
        if (items.length === 0) return '';

        return items.map((item, index) =>
            `[Context ${index + 1} | ${item.timestamp} | Score: ${item.relevance.toFixed(2)}]\n${item.content}`
        ).join('\n\n');
    }
}

export const contextProvider = new ContextProvider();
