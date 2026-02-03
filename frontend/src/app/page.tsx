'use client';

import { useEffect, useState } from 'react';
import { getApiUrl } from '@/utils/api';

interface HealthStatus {
    status: string;
    database?: string;
}

export default function Dashboard() {
    const [health, setHealth] = useState<HealthStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function fetchHealth() {
            try {
                const res = await fetch(getApiUrl('/health/ready'));
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
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
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
                            className={`w-3 h-3 rounded-full ${health?.database === 'connected' ? 'bg-emerald-500' : 'bg-slate-600'
                                }`}
                        />
                    </div>
                    <p className="text-white text-2xl font-semibold">PostgreSQL</p>
                    <p className="text-slate-500 text-sm mt-1">
                        {health?.database === 'connected' ? 'Connected' : 'Waiting...'}
                    </p>
                </div>

                {/* Vector Store Status */}
                <div className="bg-slate-800/50 backdrop-blur-xl rounded-2xl border border-slate-700/50 p-6">
                    <div className="flex items-center justify-between mb-4">
                        <span className="text-slate-400 text-sm">Vector Store</span>
                        <div className="w-3 h-3 rounded-full bg-copilot-500" />
                    </div>
                    <p className="text-white text-2xl font-semibold">Qdrant</p>
                    <p className="text-slate-500 text-sm mt-1">Phase 5 Complete</p>
                </div>
            </div>

            {/* Phase Progress */}
            <div className="bg-slate-800/50 backdrop-blur-xl rounded-2xl border border-slate-700/50 p-6">
                <h2 className="text-white text-lg font-semibold mb-4">Backend Implementation Progress</h2>
                <div className="space-y-3">
                    {[
                        { phase: 0, name: 'Scaffold & Foundations', desc: 'API, Database, Docker Compose', complete: true },
                        { phase: 1, name: 'Observability MVP', desc: 'Docker + Proxmox adapters', complete: true },
                        { phase: 2, name: 'Logging MVP', desc: 'Container log ingestion', complete: true },
                        { phase: 3, name: 'Incident Engine', desc: 'Detection + Narratives', complete: true },
                        { phase: 4, name: 'Control Plane', desc: 'Guide Mode + Actions', complete: true },
                        { phase: 5, name: 'Memory + RAG', desc: 'Historical intelligence', complete: true },
                    ].map(({ phase, name, desc, complete }) => (
                        <div key={phase} className={`flex items-center gap-4 ${!complete && 'opacity-50'}`}>
                            <div className={`w-8 h-8 rounded-full ${complete ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-700/50 text-slate-500'} flex items-center justify-center text-sm font-medium`}>
                                {complete ? '✓' : phase}
                            </div>
                            <div className="flex-1">
                                <p className="text-white">Phase {phase} — {name}</p>
                                <p className="text-slate-500 text-sm">{desc}</p>
                            </div>
                            {complete && <span className="text-emerald-400 text-sm">Complete</span>}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
