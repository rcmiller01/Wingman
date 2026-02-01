import { z } from 'zod';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

// Configuration schema with validation
const configSchema = z.object({
    // Server
    port: z.coerce.number().default(3001),
    nodeEnv: z.enum(['development', 'production', 'test']).default('development'),

    // Database
    databaseUrl: z.string().url(),

    // Qdrant
    qdrantUrl: z.string().url(),

    // LLM API Keys (at least one should be present for cloud reasoning)
    openaiApiKey: z.string().optional(),
    anthropicApiKey: z.string().optional(),
    openrouterApiKey: z.string().optional(),

    // Ollama (local model)
    ollamaHost: z.string().url().default('http://localhost:11434'),
    ollamaModel: z.string().default('qwen2.5:7b'),

    // Proxmox
    proxmoxHost: z.string().optional(),
    proxmoxUser: z.string().optional(),
    proxmoxTokenName: z.string().optional(),
    proxmoxTokenValue: z.string().optional(),
    proxmoxVerifySsl: z.coerce.boolean().default(false),
});

export type Config = z.infer<typeof configSchema>;

function loadConfig(): Config {
    const rawConfig = {
        port: process.env.BACKEND_PORT,
        nodeEnv: process.env.NODE_ENV,
        databaseUrl: process.env.DATABASE_URL,
        qdrantUrl: process.env.QDRANT_URL,
        openaiApiKey: process.env.OPENAI_API_KEY,
        anthropicApiKey: process.env.ANTHROPIC_API_KEY,
        openrouterApiKey: process.env.OPENROUTER_API_KEY,
        ollamaHost: process.env.OLLAMA_HOST,
        ollamaModel: process.env.OLLAMA_MODEL,
        proxmoxHost: process.env.PROXMOX_HOST,
        proxmoxUser: process.env.PROXMOX_USER,
        proxmoxTokenName: process.env.PROXMOX_TOKEN_NAME,
        proxmoxTokenValue: process.env.PROXMOX_TOKEN_VALUE,
        proxmoxVerifySsl: process.env.PROXMOX_VERIFY_SSL,
    };

    const result = configSchema.safeParse(rawConfig);

    if (!result.success) {
        console.error('❌ Configuration validation failed:');
        for (const issue of result.error.issues) {
            console.error(`   - ${issue.path.join('.')}: ${issue.message}`);
        }
        process.exit(1);
    }

    return result.data;
}

export const config = loadConfig();

// Check if at least one cloud API key is configured
export function hasCloudLLM(): boolean {
    return !!(config.openaiApiKey || config.anthropicApiKey || config.openrouterApiKey);
}

// Check if Proxmox is configured
export function hasProxmox(): boolean {
    return !!(config.proxmoxHost && config.proxmoxUser && config.proxmoxTokenName && config.proxmoxTokenValue);
}
