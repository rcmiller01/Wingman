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
}

export default function SettingsPage() {
    const [providers, setProviders] = useState<Provider[]>([]);
    const [settings, setSettings] = useState<LLMSettings | null>(null);
    const [models, setModels] = useState<{ [provider: string]: Model[] }>({});
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

    useEffect(() => {
        const init = async () => {
            setLoading(true);
            await loadProviders();
            await loadSettings();
            setLoading(false);
        };
        init();
    }, [loadProviders, loadSettings]);

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
                        <h2 className="text-lg font-semibold text-white mb-4">Embeddings / RAG</h2>
                        <p className="text-slate-400 text-sm mb-4">
                            Used for vector embeddings in incident search and log summaries.
                        </p>
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

                    {/* Current Configuration */}
                    {settings && (
                        <section className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
                            <h2 className="text-lg font-semibold text-white mb-4">Current Configuration</h2>
                            <div className="font-mono text-sm bg-slate-900 rounded-lg p-4 text-slate-300">
                                <pre>{JSON.stringify(settings, null, 2)}</pre>
                            </div>
                        </section>
                    )}
                </div>
            )}
        </div>
    );
}
