import { describe, it, expect } from 'vitest';
import { z } from 'zod';

// Test the config schema validation logic
describe('Config Schema', () => {
    const configSchema = z.object({
        port: z.coerce.number().default(3001),
        nodeEnv: z.enum(['development', 'production', 'test']).default('development'),
        databaseUrl: z.string().url(),
        qdrantUrl: z.string().url(),
        openaiApiKey: z.string().optional(),
        anthropicApiKey: z.string().optional(),
        openrouterApiKey: z.string().optional(),
        ollamaHost: z.string().url().default('http://localhost:11434'),
        ollamaModel: z.string().default('qwen2.5:7b'),
    });

    it('should validate a complete config', () => {
        const config = {
            port: '3001',
            nodeEnv: 'development',
            databaseUrl: 'postgresql://user:pass@localhost:5432/db',
            qdrantUrl: 'http://localhost:6333',
            openaiApiKey: 'test-api-key-placeholder',
            ollamaModel: 'qwen2.5:7b',
        };

        const result = configSchema.safeParse(config);
        expect(result.success).toBe(true);
    });

    it('should fail on invalid database URL', () => {
        const config = {
            databaseUrl: 'not-a-url',
            qdrantUrl: 'http://localhost:6333',
        };

        const result = configSchema.safeParse(config);
        expect(result.success).toBe(false);
    });

    it('should use defaults for optional values', () => {
        const config = {
            databaseUrl: 'postgresql://user:pass@localhost:5432/db',
            qdrantUrl: 'http://localhost:6333',
        };

        const result = configSchema.safeParse(config);
        expect(result.success).toBe(true);
        if (result.success) {
            expect(result.data.port).toBe(3001);
            expect(result.data.nodeEnv).toBe('development');
            expect(result.data.ollamaModel).toBe('qwen2.5:7b');
        }
    });
});
