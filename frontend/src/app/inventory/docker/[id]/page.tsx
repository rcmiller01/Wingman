'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { LogViewer } from '../../../../components/logs/LogViewer';
import { getApiUrl } from '@/lib/api-config';

interface DockerContainer {
    id: string;
    name: string;
    image: string;
    state: string;
    status: string;
    stats?: {
        cpuPercent: number;
        memoryUsageMb: number;
        memoryLimitMb: number;
        memoryPercent: number;
    };
}

export default function ContainerDetailPage() {
    const params = useParams();
    const router = useRouter();
    const id = params?.id as string;
    const [container, setContainer] = useState<DockerContainer | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!id) return;

        async function fetchContainer() {
            try {
                const res = await fetch(getApiUrl(`/api/inventory/containers/${id}`));
                if (!res.ok) throw new Error('Container not found');
                const data = await res.json();
                setContainer(data);
                setError(null);
            } catch (err: any) {
                console.error(err);
                setError(err.message);
            } finally {
                setLoading(false);
            }
        }

        fetchContainer();
        const interval = setInterval(fetchContainer, 5000);
        return () => clearInterval(interval);
    }, [id]);

    if (loading) return (
        <div className="flex items-center justify-center h-64">
            <div className="flex items-center gap-3 text-slate-400">
                <div className="w-5 h-5 border-2 border-copilot-500 border-t-transparent rounded-full animate-spin" />
                Loading container...
            </div>
        </div>
    );

    if (error) return (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400">
            Error: {error}
        </div>
    );

    if (!container) return <div className="p-8 text-center text-slate-400">Container not found</div>;

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center gap-4">
                <button
                    onClick={() => router.back()}
                    className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 transition-colors"
                    title="Go Back"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg>
                </button>
                <div>
                    <h1 className="text-2xl font-bold text-white flex items-center gap-3">
                        {container.name}
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${container.state === 'running'
                            ? 'bg-emerald-500/20 text-emerald-400'
                            : 'bg-slate-600/50 text-slate-300'
                            }`}>
                            {container.state}
                        </span>
                    </h1>
                    <p className="text-slate-400 text-sm font-mono mt-1">{container.id.substring(0, 12)} • {container.image}</p>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                {/* Sidebar / Info */}
                <div className="lg:col-span-1 space-y-4">
                    <div className="bg-slate-800/50 p-4 rounded-xl border border-slate-700/50">
                        <h3 className="text-sm font-medium text-slate-300 mb-3">Resources</h3>
                        <div className="space-y-3">
                            <div className="bg-slate-900/50 p-3 rounded-lg">
                                <div className="text-xs text-slate-500 mb-1">CPU Usage</div>
                                <div className="text-lg font-mono text-white">
                                    {container.stats ? `${container.stats.cpuPercent.toFixed(1)}%` : '-'}
                                </div>
                            </div>
                            <div className="bg-slate-900/50 p-3 rounded-lg">
                                <div className="text-xs text-slate-500 mb-1">Memory Usage</div>
                                <div className="text-lg font-mono text-white">
                                    {container.stats ? `${container.stats.memoryUsageMb}MB` : '-'}
                                </div>
                                <div className="text-xs text-slate-600 mt-1">
                                    Limit: {container.stats ? `${container.stats.memoryLimitMb}MB` : '-'}
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="bg-slate-800/50 p-4 rounded-xl border border-slate-700/50">
                        <h3 className="text-sm font-medium text-slate-300 mb-2">Details</h3>
                        <dl className="space-y-2 text-xs">
                            <div>
                                <dt className="text-slate-500">Created</dt>
                                <dd className="text-slate-300">{new Date(container.created).toLocaleDateString()}</dd>
                            </div>
                            <div>
                                <dt className="text-slate-500">Restart Count</dt>
                                <dd className="text-slate-300">{container.restartCount || 0}</dd>
                            </div>
                        </dl>
                    </div>
                </div>

                {/* Main Content - Logs */}
                <div className="lg:col-span-3">
                    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-1">
                        <LogViewer resourceRef={`docker://${container.id}`} height="h-[600px]" />
                    </div>
                </div>
            </div>
        </div>
    );
}

// Add these to interface if 'created' is missing in LogViewer's local def?
// No, standard fetching returns what backend returns.
// Backend DockerContainerInfo:
// created: Date; restartCount: number;
