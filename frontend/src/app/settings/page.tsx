'use client';

import { useCallback, useEffect, useState } from 'react';
import { getApiUrl } from '@/utils/api';

interface Provider {
    id: string;
    name: string;
    available: boolean;
    configured: boolean;
}

interface Model {
    id: string;
    name: string;
    provider: string;
    capabilities: {
        chat: boolean;
        embedding: boolean;
    };
    context_length?: number;
    size?: number;
}

interface LLMSettings {
    chat: {
        provider: string;
        model: string;
    };
    embedding: {
        provider: string;
        model: string;
    };
    embedding_dimension: number;
    embedding_locked: boolean;
    cloud_allowed: boolean;
}

interface CollectionInfo {
    name: string;
    vector_size: number | null;
    points_count: number;
    exists: boolean;
}

interface QdrantInfo {
    collections: CollectionInfo[];
    consistent: boolean;
    dimensions: number[];
    target_dimension: number;
    dimension_locked: boolean;
    embedding_blocked: boolean;
    error?: string;
}

export default function SettingsPage() {
    const [providers, setProviders] = useState<Provider[]>([]);
    const [settings, setSettings] = useState<LLMSettings | null>(null);
    const [models, setModels] = useState<{ [provider: string]: Model[] }>({});
    const [qdrantInfo, setQdrantInfo] = useState<QdrantInfo | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    // Form state
    const [chatProvider, setChatProvider] = useState('');
    const [chatModel, setChatModel] = useState('');
    const [embeddingProvider, setEmbeddingProvider] = useState('');
    const [embeddingModel, setEmbeddingModel] = useState('');

    const loadProviders = useCallback(async () => {
        try {
            const res = await fetch(getApiUrl('/settings/llm/providers'));
            if (!res.ok) throw new Error('Failed to load providers');
            const data = await res.json();
            setProviders(data);
        } catch (err: any) {
            setError(err.message);
        }
    }, []);

    const loadSettings = useCallback(async () => {
        try {
            const res = await fetch(getApiUrl('/settings/llm'));
            if (!res.ok) throw new Error('Failed to load settings');
            const data = await res.json();
            setSettings(data);
            setChatProvider(data.chat.provider);
            setChatModel(data.chat.model);
            setEmbeddingProvider(data.embedding.provider);
            setEmbeddingModel(data.embedding.model);
        } catch (err: any) {
            setError(err.message);
        }
    }, []);

    const loadModels = useCallback(async (provider: string) => {
        try {
            const res = await fetch(getApiUrl(`/settings/llm/models/${provider}`));
            if (!res.ok) throw new Error(`Failed to load ${provider} models`);
            const data = await res.json();
            setModels(prev => ({ ...prev, [provider]: data }));
        } catch (err: any) {
            console.error(`Error loading ${provider} models:`, err);
        }
    }, []);

    const loadQdrantInfo = useCallback(async () => {
        try {
            const res = await fetch(getApiUrl('/rag/collections'));
            if (!res.ok) throw new Error('Failed to load Qdrant info');
            const data = await res.json();
            setQdrantInfo(data);
        } catch (err: any) {
            console.error('Error loading Qdrant info:', err);
        }
    }, []);

    useEffect(() => {
        const init = async () => {
            setLoading(true);
            await loadProviders();
            await loadSettings();
            await loadQdrantInfo();
            setLoading(false);
        };
        init();
    }, [loadProviders, loadSettings, loadQdrantInfo]);

    // Load models when providers change or become available
    useEffect(() => {
        providers.forEach(p => {
            if (p.available && !models[p.id]) {
                loadModels(p.id);
            }
        });
    }, [providers, models, loadModels]);

    const handleSave = async (func: 'chat' | 'embedding') => {
        setSaving(true);
        setError(null);
        setSuccess(null);

        const provider = func === 'chat' ? chatProvider : embeddingProvider;
        const model = func === 'chat' ? chatModel : embeddingModel;

        try {
            const res = await fetch(getApiUrl(`/settings/llm/${func}`), {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ provider, model }),
            });
            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || 'Failed to save settings');
            }
            setSuccess(`${func} settings saved successfully`);
            setTimeout(() => setSuccess(null), 3000);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setSaving(false);
        }
    };

    const getChatModels = () => {
        return (models[chatProvider] || []).filter(m => m.capabilities.chat);
    };

    const getEmbeddingModels = () => {
        return (models[embeddingProvider] || []).filter(m => m.capabilities.embedding);
    };

    const availableProviders = providers.filter(p => p.available);

    return (
        <div className="space-y-6 max-w-4xl mx-auto">
            <header>
                <h1 className="text-2xl font-bold text-white mb-2">Settings</h1>
                <p className="text-slate-400">Configure LLM providers and models for different functions.</p>
            </header>

            {error && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400">
                    Error: {error}
                </div>
            )}

            {success && (
                <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-4 text-emerald-400">
                    {success}
                </div>
            )}

            {loading ? (
                <div className="text-slate-400 animate-pulse">Loading settings...</div>
            ) : (
                <div className="space-y-6">
                    {/* Provider Status */}
                    <section className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
                        <h2 className="text-lg font-semibold text-white mb-4">LLM Providers</h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {providers.map(provider => (
                                <div
                                    key={provider.id}
                                    className={`border rounded-lg p-4 ${
                                        provider.available
                                            ? 'border-emerald-500/30 bg-emerald-500/5'
                                            : 'border-slate-700/40 bg-slate-900/30 opacity-60'
                                    }`}
                                >
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <h3 className="text-white font-medium">{provider.name}</h3>
                                            <p className="text-slate-400 text-sm mt-1">
                                                {provider.available
                                                    ? `${(models[provider.id] || []).length} models available`
                                                    : provider.configured
                                                    ? 'Not connected'
                                                    : 'Not configured'}
                                            </p>
                                        </div>
                                        <div className={`w-3 h-3 rounded-full ${
                                            provider.available ? 'bg-emerald-500' : 'bg-slate-600'
                                        }`} />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>

                    {/* Chat Model Selection */}
                    <section className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
                        <h2 className="text-lg font-semibold text-white mb-4">Chat / Narrative Generation</h2>
                        <p className="text-slate-400 text-sm mb-4">
                            Used for generating incident narratives and analysis.
                        </p>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-2">Provider</label>
                                <select
                                    value={chatProvider}
                                    onChange={(e) => {
                                        setChatProvider(e.target.value);
                                        setChatModel(''); // Reset model when provider changes
                                    }}
                                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-copilot-500"
                                >
                                    {availableProviders.map(p => (
                                        <option key={p.id} value={p.id}>{p.name}</option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-2">Model</label>
                                <select
                                    value={chatModel}
                                    onChange={(e) => setChatModel(e.target.value)}
                                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-copilot-500"
                                >
                                    <option value="">-- Select Model --</option>
                                    {getChatModels().map(m => (
                                        <option key={m.id} value={m.id}>
                                            {m.name} {m.context_length ? `(${Math.round(m.context_length / 1000)}K ctx)` : ''}
                                        </option>
                                    ))}
                                </select>
                            </div>
                        </div>
                        <div className="mt-4 flex justify-end">
                            <button
                                onClick={() => handleSave('chat')}
                                disabled={saving || !chatModel}
                                className="px-4 py-2 bg-copilot-600 text-white rounded-lg text-sm font-medium hover:bg-copilot-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                            >
                                {saving ? 'Saving...' : 'Save Chat Settings'}
                            </button>
                        </div>
                    </section>

                    {/* Embedding Model Selection */}
                    <section className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="text-lg font-semibold text-white">Embeddings / RAG</h2>
                            {settings && (
                                <div className="flex items-center gap-2">
                                    <span className="text-xs text-slate-400">
                                        Dimension: {settings.embedding_dimension}
                                    </span>
                                    {settings.embedding_locked && (
                                        <span className="text-xs bg-amber-500/20 text-amber-400 px-2 py-0.5 rounded border border-amber-500/30">
                                            Locked
                                        </span>
                                    )}
                                </div>
                            )}
                        </div>
                        <p className="text-slate-400 text-sm mb-4">
                            Used for vector embeddings in incident search and log summaries.
                        </p>
                        {settings?.embedding_locked && (
                            <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 mb-4 text-sm text-amber-400">
                                Embedding dimension is locked at {settings.embedding_dimension}. Changing to a model with different dimensions requires recreating Qdrant collections.
                            </div>
                        )}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-2">Provider</label>
                                <select
                                    value={embeddingProvider}
                                    onChange={(e) => {
                                        setEmbeddingProvider(e.target.value);
                                        setEmbeddingModel(''); // Reset model when provider changes
                                    }}
                                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-copilot-500"
                                >
                                    {availableProviders.map(p => (
                                        <option key={p.id} value={p.id}>{p.name}</option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-2">Model</label>
                                <select
                                    value={embeddingModel}
                                    onChange={(e) => setEmbeddingModel(e.target.value)}
                                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-copilot-500"
                                >
                                    <option value="">-- Select Model --</option>
                                    {getEmbeddingModels().map(m => (
                                        <option key={m.id} value={m.id}>{m.name}</option>
                                    ))}
                                </select>
                            </div>
                        </div>
                        <div className="mt-4 flex justify-end">
                            <button
                                onClick={() => handleSave('embedding')}
                                disabled={saving || !embeddingModel}
                                className="px-4 py-2 bg-copilot-600 text-white rounded-lg text-sm font-medium hover:bg-copilot-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                            >
                                {saving ? 'Saving...' : 'Save Embedding Settings'}
                            </button>
                        </div>
                    </section>

                    {/* System Status */}
                    {settings && (
                        <section className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
                            <h2 className="text-lg font-semibold text-white mb-4">System Status</h2>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <div className="bg-slate-900/50 rounded-lg p-4">
                                    <div className="text-slate-400 text-xs uppercase tracking-wider mb-1">Embedding Dimension</div>
                                    <div className="text-white text-lg font-mono">{settings.embedding_dimension}</div>
                                </div>
                                <div className="bg-slate-900/50 rounded-lg p-4">
                                    <div className="text-slate-400 text-xs uppercase tracking-wider mb-1">Dimension Status</div>
                                    <div className={`text-lg font-medium ${settings.embedding_locked ? 'text-amber-400' : 'text-emerald-400'}`}>
                                        {settings.embedding_locked ? 'Locked' : 'Unlocked'}
                                    </div>
                                </div>
                                <div className="bg-slate-900/50 rounded-lg p-4">
                                    <div className="text-slate-400 text-xs uppercase tracking-wider mb-1">Cloud LLM</div>
                                    <div className={`text-lg font-medium ${settings.cloud_allowed ? 'text-emerald-400' : 'text-slate-500'}`}>
                                        {settings.cloud_allowed ? 'Enabled' : 'Disabled'}
                                    </div>
                                </div>
                            </div>
                            {!settings.cloud_allowed && (
                                <p className="text-slate-500 text-xs mt-4">
                                    Set ALLOW_CLOUD_LLM=true in environment to enable cloud providers like OpenRouter.
                                </p>
                            )}
                        </section>
                    )}

                    {/* Qdrant Vector Store */}
                    {qdrantInfo && (
                        <section className={`rounded-xl border p-6 ${
                            qdrantInfo.embedding_blocked
                                ? 'bg-red-900/20 border-red-500/50'
                                : 'bg-slate-800/50 border-slate-700/50'
                        }`}>
                            <div className="flex items-center justify-between mb-4">
                                <h2 className="text-lg font-semibold text-white">Vector Store (Qdrant)</h2>
                                <div className="flex items-center gap-2">
                                    {qdrantInfo.embedding_blocked && (
                                        <span className="text-xs bg-red-500/30 text-red-300 px-2 py-0.5 rounded border border-red-500/50 font-medium">
                                            BLOCKED
                                        </span>
                                    )}
                                    {!qdrantInfo.consistent && !qdrantInfo.embedding_blocked && (
                                        <span className="text-xs bg-red-500/20 text-red-400 px-2 py-0.5 rounded border border-red-500/30">
                                            Dimension Mismatch
                                        </span>
                                    )}
                                </div>
                            </div>
                            {qdrantInfo.embedding_blocked && (
                                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 mb-4 text-sm text-red-400">
                                    <strong>Embedding operations are BLOCKED</strong> due to inconsistent collection dimensions.
                                    All indexing and search operations will fail until this is resolved.
                                    Use the API endpoint <code className="bg-red-900/50 px-1 rounded">POST /api/rag/collections/recreate</code> to fix.
                                </div>
                            )}
                            <div className="space-y-3">
                                {qdrantInfo.collections.map(collection => (
                                    <div
                                        key={collection.name}
                                        className={`border rounded-lg p-4 ${
                                            collection.exists
                                                ? 'border-slate-700/40 bg-slate-900/30'
                                                : 'border-red-500/30 bg-red-500/5'
                                        }`}
                                    >
                                        <div className="flex items-center justify-between">
                                            <div>
                                                <h3 className="text-white font-medium font-mono text-sm">{collection.name}</h3>
                                                <div className="flex gap-4 mt-1 text-sm text-slate-400">
                                                    {collection.exists ? (
                                                        <>
                                                            <span>Dimension: <span className="text-white font-mono">{collection.vector_size}</span></span>
                                                            <span>Documents: <span className="text-white font-mono">{collection.points_count.toLocaleString()}</span></span>
                                                        </>
                                                    ) : (
                                                        <span className="text-red-400">Collection not found</span>
                                                    )}
                                                </div>
                                            </div>
                                            <div className={`w-3 h-3 rounded-full ${
                                                collection.exists ? 'bg-emerald-500' : 'bg-red-500'
                                            }`} />
                                        </div>
                                    </div>
                                ))}
                            </div>
                            {qdrantInfo.error && (
                                <p className="text-red-400 text-sm mt-3">Error: {qdrantInfo.error}</p>
                            )}
                            <p className="text-slate-500 text-xs mt-4">
                                Target dimension: {qdrantInfo.target_dimension}. To recreate collections with a new dimension, use the API endpoint POST /api/rag/collections/recreate.
                            </p>
                        </section>
                    )}
                </div>
            )}
        </div>
    );
}
