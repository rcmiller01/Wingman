'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

import { getApiUrl } from '@/utils/api';

interface Incident {
    id: string;
    severity: string;
    status: string;
    affectedResources: string[];
    detectedAt: string;
    narrative?: {
        narrativeText: string;
    };
}

export default function IncidentsPage() {
    const [incidents, setIncidents] = useState<Incident[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch(getApiUrl('/incidents?status=open,investigating,mitigated'))
            .then(res => res.json())
            .then(data => {
                const list = Array.isArray(data) ? data : data.incidents;
                const mapped = (list || []).map(mapIncidentFromApi);
                setIncidents(mapped);
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setLoading(false);
            });
    }, []);

    return (
        <div className="space-y-6 max-w-5xl mx-auto">
            <header className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white mb-2">Incidents</h1>
                    <p className="text-slate-400">Manage and investigate infrastructure issues</p>
                </div>
            </header>

            {loading ? (
                <div className="text-slate-400 animate-pulse">Loading incidents...</div>
            ) : incidents.length === 0 ? (
                <div className="bg-slate-800/50 rounded-xl p-12 text-center border border-slate-700/50 backdrop-blur-sm">
                    <div className="text-5xl mb-6 opacity-80">✅</div>
                    <h3 className="text-xl font-medium text-white mb-2">All Systems Operational</h3>
                    <p className="text-slate-400">No open incidents detected.</p>
                </div>
            ) : (
                <div className="grid gap-4">
                    {incidents.map(incident => (
                        <Link
                            key={incident.id}
                            href={`/incidents/${incident.id}`}
                            className="block bg-slate-800/50 hover:bg-slate-800 border border-slate-700/50 hover:border-slate-600 rounded-xl p-6 transition-all group"
                        >
                            <div className="flex items-start justify-between">
                                <div className="space-y-2">
                                    <div className="flex items-center gap-3">
                                        <SeverityBadge severity={incident.severity} />
                                        <h3 className="text-lg font-bold text-white group-hover:text-copilot-400 transition-colors">
                                            {extractTitle(incident.narrative?.narrativeText)}
                                        </h3>
                                    </div>
                                    <div className="flex items-center gap-3 text-sm text-slate-400">
                                        <span className="flex items-center gap-1.5">
                                            <span>📦</span>
                                            {incident.affectedResources.join(', ')}
                                        </span>
                                        <span>•</span>
                                        <span>{new Date(incident.detectedAt).toLocaleString()}</span>
                                    </div>
                                </div>
                                <StatusBadge status={incident.status} />
                            </div>
                        </Link>
                    ))}
                </div>
            )}
        </div>
    );
}

function mapIncidentFromApi(payload: any): Incident {
    return {
        id: payload.id,
        severity: payload.severity,
        status: payload.status,
        affectedResources: payload.affected_resources || [],
        detectedAt: payload.detected_at,
        narrative: payload.narrative
            ? {
                narrativeText: payload.narrative.narrative_text,
            }
            : undefined,
    };
}

function extractTitle(narrative?: string) {
    if (!narrative) return 'Untitled Incident';
    // Extract first line or ## header
    const match = narrative.match(/^##\s+(.+)$/m) || narrative.match(/^(.+)$/m);
    return match ? match[1] : 'Incident';
}

function SeverityBadge({ severity }: { severity: string }) {
    const colors = {
        critical: 'bg-red-500/20 text-red-400 border-red-500/30',
        high: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
        medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
        low: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    };
    return (
        <span className={`px-2.5 py-0.5 rounded text-xs font-bold border ${colors[severity as keyof typeof colors] || colors.low} uppercase tracking-wider`}>
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
        <span className={`px-3 py-1 rounded-full text-sm font-medium border ${colors[status as keyof typeof colors] || colors.open}`}>
            {status}
        </span>
    );
}
