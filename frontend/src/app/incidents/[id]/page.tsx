'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';

interface Incident {
    id: string;
    severity: string;
    status: string;
    affectedResources: string[];
    detectedAt: string;
    narrative?: {
        narrativeText: string;
        rootCauseHypothesis?: string;
    };
}

export default function IncidentDetailPage() {
    const { id } = useParams();
    const [incident, setIncident] = useState<Incident | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!id) return;
        fetch(`/api/incidents/${id}`)
            .then(res => {
                if (!res.ok) throw new Error('Failed to fetch incident');
                return res.json();
            })
            .then(data => {
                setIncident(data);
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setLoading(false);
            });
    }, [id]);

    if (loading) {
        return (
            <div className="max-w-4xl mx-auto animate-pulse space-y-8">
                <div className="h-8 bg-slate-800 rounded w-1/4"></div>
                <div className="h-64 bg-slate-800 rounded-xl"></div>
            </div>
        );
    }

    if (!incident) {
        return (
            <div className="max-w-4xl mx-auto text-center py-20">
                <h2 className="text-xl text-white">Incident not found</h2>
                <Link href="/incidents" className="text-copilot-400 hover:text-copilot-300 mt-4 inline-block">
                    Return to Incidents
                </Link>
            </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto space-y-8">
            <nav className="flex items-center justify-between">
                <Link href="/incidents" className="text-slate-400 hover:text-white flex items-center gap-2 transition-colors">
                    <span>←</span> Back to Incidents
                </Link>
                <StatusBadge status={incident.status} />
            </nav>

            <div className="bg-slate-800/50 rounded-xl p-8 border border-slate-700/50 backdrop-blur-sm shadow-xl">
                <div className="flex items-center gap-4 mb-8 pb-6 border-b border-slate-700/50">
                    <SeverityBadge severity={incident.severity} />
                    <span className="text-slate-400 font-mono text-sm">{new Date(incident.detectedAt).toLocaleString()}</span>
                    <span className="text-slate-600 font-mono text-xs ml-auto">ID: {incident.id}</span>
                </div>

                <div className="prose prose-invert max-w-none">
                    <div className="whitespace-pre-wrap font-sans text-slate-300 leading-relaxed text-lg">
                        {incident.narrative?.narrativeText}
                    </div>
                </div>

                {incident.narrative?.rootCauseHypothesis && (
                    <div className="mt-8 bg-slate-900/50 rounded-lg p-4 border border-slate-700/30">
                        <h4 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-2">Root Cause Hypothesis</h4>
                        <p className="text-copilot-300">{incident.narrative.rootCauseHypothesis}</p>
                    </div>
                )}
            </div>

            {/* Affected Resources */}
            <div>
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    <span>📦</span> Affected Resources
                </h3>
                <div className="grid gap-3">
                    {incident.affectedResources.map(ref => (
                        <ResourceLink key={ref} refId={ref} />
                    ))}
                </div>
            </div>
        </div>
    );
}

function ResourceLink({ refId }: { refId: string }) {
    // Parse resource ref (e.g., docker://abc123456)
    let href = '#';
    let label = refId;
    let icon = '🔧';

    if (refId.startsWith('docker://')) {
        const id = refId.split('docker://')[1];
        href = `/inventory/docker/${id}`;
        label = `Docker Container: ${id.substring(0, 12)}`;
        icon = '🐳';
    } else if (refId.startsWith('proxmox://')) {
        // href = `/inventory/proxmox/...`; // Not implemented yet
        label = `Proxmox Resource: ${refId.split('proxmox://')[1]}`;
        icon = '🖥️';
    }

    return (
        <Link
            href={href}
            className="flex items-center gap-3 bg-slate-800/30 hover:bg-slate-800 border border-slate-700/30 hover:border-slate-600 rounded-lg p-4 transition-all group"
        >
            <span className="text-2xl">{icon}</span>
            <span className="font-mono text-slate-300 group-hover:text-white transition-colors">{label}</span>
            <span className="ml-auto text-slate-500 group-hover:text-slate-400">View Details →</span>
        </Link>
    );
}

function SeverityBadge({ severity }: { severity: string }) {
    const colors = {
        critical: 'bg-red-500/20 text-red-400 border-red-500/30',
        high: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
        medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
        low: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    };
    return (
        <span className={`px-3 py-1 rounded text-sm font-bold border ${colors[severity as keyof typeof colors] || colors.low} uppercase tracking-wider shadow-sm`}>
            {severity}
        </span>
    );
}

function StatusBadge({ status }: { status: string }) {
    const colors = {
        open: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
        resolved: 'bg-slate-700/50 text-slate-400 border-slate-600/50',
    };
    return (
        <span className={`px-4 py-1.5 rounded-full text-sm font-medium border ${colors[status as keyof typeof colors] || colors.open} shadow-sm`}>
            {status}
        </span>
    );
}
