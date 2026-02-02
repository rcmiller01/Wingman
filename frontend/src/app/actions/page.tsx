'use client';

import { useCallback, useEffect, useState } from 'react';
import { getApiUrl } from '@/lib/api-config';

interface Plan {
    id: string;
    incident_id?: string | null;
    action_template: string;
    target_resource: string;
    parameters: Record<string, any>;
    status: string;
    requested_at: string;
    approved_at?: string | null;
    executed_at?: string | null;
    completed_at?: string | null;
    result?: Record<string, any> | null;
    error?: string | null;
}

export default function ActionsPage() {
    const [plans, setPlans] = useState<Plan[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [busyId, setBusyId] = useState<string | null>(null);

    const loadPlans = useCallback(async () => {
        try {
            const res = await fetch(getApiUrl('/api/plans'));
            if (!res.ok) throw new Error('Failed to load plans');
            const data = await res.json();
            setPlans(data.plans || []);
            setError(null);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadPlans();
        const interval = setInterval(loadPlans, 10000);
        return () => clearInterval(interval);
    }, [loadPlans]);

    const handleAction = async (planId: string, action: 'approve' | 'reject') => {
        setBusyId(planId);
        try {
            const res = await fetch(getApiUrl(`/api/plans/${planId}/${action}`), { method: 'POST' });
            if (!res.ok) throw new Error('Action failed');
            await loadPlans();
        } catch (err: any) {
            setError(err.message);
        } finally {
            setBusyId(null);
        }
    };

    const pendingPlans = plans.filter(plan => plan.status === 'pending');
    const historyPlans = plans.filter(plan => plan.status !== 'pending');

    return (
        <div className="space-y-6 max-w-5xl mx-auto">
            <header className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white mb-2">Action Approvals</h1>
                    <p className="text-slate-400">Approve or reject queued remediation steps.</p>
                </div>
            </header>

            {loading ? (
                <div className="text-slate-400 animate-pulse">Loading actions...</div>
            ) : error ? (
                <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400">
                    Error: {error}
                </div>
            ) : (
                <div className="space-y-6">
                    <section className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
                        <h2 className="text-lg font-semibold text-white mb-4">Pending Approval</h2>
                        {pendingPlans.length === 0 ? (
                            <p className="text-slate-400">No pending actions.</p>
                        ) : (
                            <div className="space-y-4">
                                {pendingPlans.map(plan => (
                                    <div key={plan.id} className="bg-slate-900/50 border border-slate-700/40 rounded-lg p-4">
                                        <div className="flex items-start justify-between">
                                            <div>
                                                <div className="flex items-center gap-2 text-sm text-slate-400">
                                                    <span className="font-mono">{plan.id.slice(0, 8)}</span>
                                                    {plan.incident_id && (
                                                        <span className="text-slate-500">Incident {plan.incident_id.slice(0, 8)}</span>
                                                    )}
                                                </div>
                                                <h3 className="text-white font-medium mt-1">{formatAction(plan.action_template)}</h3>
                                                <p className="text-slate-400 text-sm mt-1">{plan.target_resource}</p>
                                                <p className="text-slate-500 text-xs mt-2">
                                                    Requested {new Date(plan.requested_at).toLocaleString()}
                                                </p>
                                            </div>
                                            <StatusBadge status={plan.status} />
                                        </div>
                                        <div className="mt-4 flex gap-2">
                                            <button
                                                onClick={() => handleAction(plan.id, 'approve')}
                                                disabled={busyId === plan.id}
                                                className="px-4 py-2 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded-lg text-sm font-medium hover:bg-emerald-500/30 disabled:opacity-50"
                                            >
                                                Approve
                                            </button>
                                            <button
                                                onClick={() => handleAction(plan.id, 'reject')}
                                                disabled={busyId === plan.id}
                                                className="px-4 py-2 bg-red-500/10 text-red-400 border border-red-500/30 rounded-lg text-sm font-medium hover:bg-red-500/20 disabled:opacity-50"
                                            >
                                                Reject
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </section>

                    <section className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
                        <h2 className="text-lg font-semibold text-white mb-4">Action History</h2>
                        {historyPlans.length === 0 ? (
                            <p className="text-slate-400">No completed actions yet.</p>
                        ) : (
                            <div className="space-y-3">
                                {historyPlans.map(plan => (
                                    <div key={plan.id} className="flex items-start justify-between border border-slate-700/40 rounded-lg p-4">
                                        <div>
                                            <div className="flex items-center gap-2 text-sm text-slate-400">
                                                <span className="font-mono">{plan.id.slice(0, 8)}</span>
                                                {plan.incident_id && (
                                                    <span className="text-slate-500">Incident {plan.incident_id.slice(0, 8)}</span>
                                                )}
                                            </div>
                                            <h3 className="text-white font-medium mt-1">{formatAction(plan.action_template)}</h3>
                                            <p className="text-slate-400 text-sm mt-1">{plan.target_resource}</p>
                                            {plan.result && (
                                                <p className="text-slate-500 text-xs mt-2">
                                                    Result: {plan.result.message || 'Completed'}
                                                </p>
                                            )}
                                            {plan.error && (
                                                <p className="text-red-400 text-xs mt-2">Error: {plan.error}</p>
                                            )}
                                        </div>
                                        <StatusBadge status={plan.status} />
                                    </div>
                                ))}
                            </div>
                        )}
                    </section>
                </div>
            )}
        </div>
    );
}

function formatAction(action: string) {
    return action.replace(/_/g, ' ');
}

function StatusBadge({ status }: { status: string }) {
    const colors = {
        pending: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
        approved: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
        executing: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
        completed: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
        failed: 'bg-red-500/20 text-red-400 border-red-500/30',
    };
    return (
        <span className={`px-3 py-1 rounded-full text-xs font-medium border ${colors[status as keyof typeof colors] || colors.pending}`}>
            {status}
        </span>
    );
}
