'use client';

import { useEffect, useState } from 'react';

interface HealthStatus {
    status: string;
    checks?: {
        db: boolean;
        qdrant: boolean;
        cloudLlm: string;
        ollamaModel: string;
        proxmox: string;
    };
}

export default function Dashboard() {
    const [health, setHealth] = useState<HealthStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function fetchHealth() {
            try {
                const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001';
                const res = await fetch(`${apiUrl}/ready`);
                const data = await res.json();
                setHealth(data);
            } catch (err) {
                setError('Failed to connect to backend');
            } finally {
                setLoading(false);
            }
        }

        fetchHealth();
        const interval = setInterval(fetchHealth, 10000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="space-y-8">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold text-white mb-2">Dashboard</h1>
                <p className="text-slate-400">System health and overview</p>
            </div>

            {/* Status Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* Backend Status */}
                <div className="bg-slate-800/50 backdrop-blur-xl rounded-2xl border border-slate-700/50 p-6">
                    <div className="flex items-center justify-between mb-4">
                        <span className="text-slate-400 text-sm">Backend</span>
                        {loading ? (
                            <div className="w-3 h-3 rounded-full bg-yellow-500 animate-pulse" />
                        ) : error ? (
                            <div className="w-3 h-3 rounded-full bg-red-500" />
                        ) : (
                            <div className="w-3 h-3 rounded-full bg-emerald-500" />
                        )}
                    </div>
                    <p className="text-white text-2xl font-semibold">
                        {loading ? 'Connecting...' : error ? 'Offline' : 'Online'}
                    </p>
                    <p className="text-slate-500 text-sm mt-1">
                        {health?.status === 'ready' ? 'All systems operational' : 'Degraded'}
                    </p>
                </div>

                {/* Database Status */}
                <div className="bg-slate-800/50 backdrop-blur-xl rounded-2xl border border-slate-700/50 p-6">
                    <div className="flex items-center justify-between mb-4">
                        <span className="text-slate-400 text-sm">Database</span>
                        <div
                            className={`w-3 h-3 rounded-full ${health?.checks?.db ? 'bg-emerald-500' : 'bg-slate-600'
                                }`}
                        />
                    </div>
                    <p className="text-white text-2xl font-semibold">PostgreSQL</p>
                    <p className="text-slate-500 text-sm mt-1">
                        {health?.checks?.db ? 'Connected' : 'Waiting...'}
                    </p>
                </div>

                {/* Qdrant Status */}
                <div className="bg-slate-800/50 backdrop-blur-xl rounded-2xl border border-slate-700/50 p-6">
                    <div className="flex items-center justify-between mb-4">
                        <span className="text-slate-400 text-sm">Vector Store</span>
                        <div
                            className={`w-3 h-3 rounded-full ${health?.checks?.qdrant ? 'bg-emerald-500' : 'bg-slate-600'
                                }`}
                        />
                    </div>
                    <p className="text-white text-2xl font-semibold">Qdrant</p>
                    <p className="text-slate-500 text-sm mt-1">
                        {health?.checks?.qdrant ? 'Connected' : 'Waiting...'}
                    </p>
                </div>

                {/* LLM Status */}
                <div className="bg-slate-800/50 backdrop-blur-xl rounded-2xl border border-slate-700/50 p-6">
                    <div className="flex items-center justify-between mb-4">
                        <span className="text-slate-400 text-sm">Local LLM</span>
                        <div className="w-3 h-3 rounded-full bg-copilot-500" />
                    </div>
                    <p className="text-white text-2xl font-semibold truncate">
                        {health?.checks?.ollamaModel || 'Not set'}
                    </p>
                    <p className="text-slate-500 text-sm mt-1">Ollama</p>
                </div>
            </div>

            {/* Configuration Status */}
            <div className="bg-slate-800/50 backdrop-blur-xl rounded-2xl border border-slate-700/50 p-6">
                <h2 className="text-white text-lg font-semibold mb-4">Configuration</h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="flex items-center gap-3">
                        <div
                            className={`w-8 h-8 rounded-lg flex items-center justify-center ${health?.checks?.cloudLlm === 'configured'
                                    ? 'bg-emerald-500/20 text-emerald-400'
                                    : 'bg-slate-700/50 text-slate-500'
                                }`}
                        >
                            ☁️
                        </div>
                        <div>
                            <p className="text-white text-sm">Cloud LLM</p>
                            <p className="text-slate-500 text-xs">
                                {health?.checks?.cloudLlm === 'configured' ? 'Ready' : 'Not configured'}
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center gap-3">
                        <div
                            className={`w-8 h-8 rounded-lg flex items-center justify-center ${health?.checks?.proxmox === 'configured'
                                    ? 'bg-emerald-500/20 text-emerald-400'
                                    : 'bg-slate-700/50 text-slate-500'
                                }`}
                        >
                            🖥️
                        </div>
                        <div>
                            <p className="text-white text-sm">Proxmox</p>
                            <p className="text-slate-500 text-xs">
                                {health?.checks?.proxmox === 'configured' ? 'Ready' : 'Not configured'}
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-slate-700/50 text-slate-500">
                            🐳
                        </div>
                        <div>
                            <p className="text-white text-sm">Docker</p>
                            <p className="text-slate-500 text-xs">Phase 1</p>
                        </div>
                    </div>

                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-slate-700/50 text-slate-500">
                            📝
                        </div>
                        <div>
                            <p className="text-white text-sm">Logs</p>
                            <p className="text-slate-500 text-xs">Phase 2</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Phase Progress */}
            <div className="bg-slate-800/50 backdrop-blur-xl rounded-2xl border border-slate-700/50 p-6">
                <h2 className="text-white text-lg font-semibold mb-4">Implementation Progress</h2>
                <div className="space-y-3">
                    <div className="flex items-center gap-4">
                        <div className="w-8 h-8 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-sm font-medium">
                            ✓
                        </div>
                        <div className="flex-1">
                            <p className="text-white">Phase 0 — Scaffold & Foundations</p>
                            <p className="text-slate-500 text-sm">API, Database, Docker Compose</p>
                        </div>
                        <span className="text-emerald-400 text-sm">Current</span>
                    </div>
                    {[
                        { phase: 1, name: 'Observability MVP', desc: 'Proxmox + Docker adapters' },
                        { phase: 2, name: 'Logging MVP', desc: 'Container log ingestion' },
                        { phase: 3, name: 'Incident Engine', desc: 'Detection + Narratives' },
                        { phase: 4, name: 'Control Plane', desc: 'Guide Mode + Actions' },
                        { phase: 5, name: 'Memory + RAG', desc: 'Historical intelligence' },
                    ].map(({ phase, name, desc }) => (
                        <div key={phase} className="flex items-center gap-4 opacity-50">
                            <div className="w-8 h-8 rounded-full bg-slate-700/50 text-slate-500 flex items-center justify-center text-sm font-medium">
                                {phase}
                            </div>
                            <div className="flex-1">
                                <p className="text-white">Phase {phase} — {name}</p>
                                <p className="text-slate-500 text-sm">{desc}</p>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
