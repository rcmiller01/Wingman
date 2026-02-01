
import { config } from '../config/index.js';

interface SearchResult {
    id: string | number;
    score: number;
    payload: Record<string, any>;
    version: number;
}

const COLLECTION_NAME = 'memories';
const EMBEDDING_MODEL = 'nomic-embed-text';
const VECTOR_SIZE = 768; // nomic-embed-text-v1.5 is 768

export class QdrantService {
    private url: string;

    constructor() {
        this.url = config.qdrantUrl; // http://qdrant:6333
    }

    async init() {
        try {
            // Check if collection exists
            const response = await fetch(`${this.url}/collections/${COLLECTION_NAME}`);
            if (!response.ok) {
                if (response.status === 404) {
                    console.log(`DEBUG: QDRANT: Creating collection: ${COLLECTION_NAME}`);
                    await this.createCollection();
                } else {
                    console.error('Failed to check Qdrant collection:', response.statusText);
                }
            }
        } catch (error) {
            console.error('Qdrant init failed:', error);
        }
    }

    private async createCollection() {
        const response = await fetch(`${this.url}/collections/${COLLECTION_NAME}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                vectors: {
                    size: VECTOR_SIZE,
                    distance: 'Cosine'
                }
            })
        });

        if (!response.ok) {
            throw new Error(`Failed to create collection: ${response.statusText}`);
        }
    }

    async storeMemory(content: string, metadata: Record<string, any>) {
        console.log(`DEBUG: QDRANT: Storing memory for ${metadata.resourceRef}...`);
        const embedding = await this.getEmbedding(content);
        if (!embedding) {
            console.error('DEBUG: QDRANT: Failed to get embedding for memory.');
            return;
        }

        const point = {
            id: crypto.randomUUID(),
            vector: embedding,
            payload: {
                content,
                ...metadata,
                timestamp: new Date().toISOString()
            }
        };

        console.log(`DEBUG: QDRANT: Sending vector to Qdrant (size: ${embedding.length})...`);
        try {
            const response = await fetch(`${this.url}/collections/${COLLECTION_NAME}/points?wait=true`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    points: [point]
                })
            });

            if (!response.ok) {
                console.error('DEBUG: QDRANT: Failed to store memory in Qdrant:', await response.text());
            } else {
                console.log(`DEBUG: QDRANT: Stored memory in Qdrant: ${metadata.resourceRef || 'unknown'}`);
            }
        } catch (error) {
            console.error('DEBUG: QDRANT: Qdrant storage exception:', error);
        }
    }

    async search(query: string, limit = 5): Promise<SearchResult[]> {
        const embedding = await this.getEmbedding(query);
        if (!embedding) return [];

        try {
            const response = await fetch(`${this.url}/collections/${COLLECTION_NAME}/points/search`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    vector: embedding,
                    limit,
                    with_payload: true
                })
            });

            if (!response.ok) {
                console.error('Failed to search memories:', await response.text());
                return [];
            }

            const data: any = await response.json();
            return data.result || [];
        } catch (error) {
            console.error('Qdrant search exception:', error);
            return [];
        }
    }

    private async getEmbedding(text: string): Promise<number[] | null> {
        const EMBEDDING_TIMEOUT_MS = 30000; // 30 seconds for embeddings
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), EMBEDDING_TIMEOUT_MS);

        try {
            const response = await fetch(`${config.ollamaHost}/api/embeddings`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model: EMBEDDING_MODEL,
                    prompt: text
                }),
                signal: controller.signal
            });

            if (!response.ok) {
                console.error(`[Qdrant] Ollama embedding failed (${response.status}): ${await response.text()}`);
                return null;
            }

            const data: any = await response.json();
            if (!data.embedding) console.error('[Qdrant] Ollama response missing embedding field');
            return data.embedding;
        } catch (error: any) {
            if (error.name === 'AbortError') {
                console.error('[Qdrant] Embedding generation timed out');
                return null;
            }
            console.error('[Qdrant] Failed to generate embedding:', error);
            return null;
        } finally {
            clearTimeout(timeout);
        }
    }
}

export const qdrantService = new QdrantService();
