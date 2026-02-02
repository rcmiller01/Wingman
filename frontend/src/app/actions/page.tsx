'use client';

import { useCallback, useEffect, useState } from 'react';
import { getApiUrl } from '@/utils/api';

interface TodoStep {
    id: string;
    incident_id?: string | null;
    plan_id?: string | null;
    action_template: string;
    target_resource: string;
    parameters: Record<string, any>; // JSON
    description?: string | null;
    verification?: string | null;
    status: string;
    created_at: string;
    approved_at?: string | null;
    executed_at?: string | null;
    completed_at?: string | null;
    result?: Record<string, any> | null;
    error?: string | null;
}

export default function ActionsPage() {
    const [todos, setTodos] = useState<TodoStep[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [busyId, setBusyId] = useState<string | null>(null);

    const loadTodos = useCallback(async () => {
        try {
            const res = await fetch(getApiUrl('/todos'));
            if (!res.ok) throw new Error('Failed to load actions');
            const data = await res.json();
            setTodos(data || []);
            setError(null);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadTodos();
        const interval = setInterval(loadTodos, 5000); // Poll every 5s
        return () => clearInterval(interval);
    }, [loadTodos]);

    const handleAction = async (todoId: string, action: 'approve' | 'reject') => {
        setBusyId(todoId);
        try {
            const res = await fetch(getApiUrl(`/todos/${todoId}/${action}`), { method: 'POST' });
            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || 'Action failed');
            }
            // Optimistic update or reload
            await loadTodos();
        } catch (err: any) {
            setError(err.message);
            // Clear error after 5s
            setTimeout(() => setError(null), 5000);
        } finally {
            setBusyId(null);
        }
    };

    const pendingTodos = todos.filter(t => t.status === 'pending');
    const historyTodos = todos.filter(t => t.status !== 'pending');

    return (
        <div className="space-y-6 max-w-5xl mx-auto">
            <header className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white mb-2">Action Approvals</h1>
                    <p className="text-slate-400">Approve or reject queued remediation steps.</p>
                </div>
            </header>

            {error && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400">
                    Error: {error}
                </div>
            )}

            {loading && todos.length === 0 ? (
                <div className="text-slate-400 animate-pulse">Loading actions...</div>
            ) : (
                <div className="space-y-6">
                    <section className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
                        <h2 className="text-lg font-semibold text-white mb-4">Pending Approval</h2>
                        {pendingTodos.length === 0 ? (
                            <p className="text-slate-400">No pending actions.</p>
                        ) : (
                            <div className="space-y-4">
                                {pendingTodos.map(todo => (
                                    <div key={todo.id} className="bg-slate-900/50 border border-slate-700/40 rounded-lg p-4 transition-all hover:bg-slate-900/70">
                                        <div className="flex items-start justify-between">
                                            <div>
                                                <div className="flex items-center gap-2 text-sm text-slate-400">
                                                    <span className="font-mono bg-slate-800 px-1.5 rounded">{todo.id.slice(0, 8)}</span>
                                                    {todo.incident_id && (
                                                        <span className="text-slate-500">Incident {todo.incident_id.slice(0, 8)}</span>
                                                    )}
                                                </div>
                                                <h3 className="text-white font-medium mt-1 text-lg">{formatAction(todo.action_template)}</h3>
                                                <p className="text-slate-400 text-sm mt-1 font-mono">{todo.target_resource}</p>
                                                {todo.description && (
                                                    <p className="text-slate-500 text-sm mt-2 italic">"{todo.description}"</p>
                                                )}
                                                <p className="text-slate-500 text-xs mt-2">
                                                    Requested {new Date(todo.created_at).toLocaleString()}
                                                </p>
                                            </div>
                                            <StatusBadge status={todo.status} />
                                        </div>
                                        <div className="mt-4 flex gap-2">
                                            <button
                                                onClick={() => handleAction(todo.id, 'approve')}
                                                disabled={busyId === todo.id}
                                                className="px-4 py-2 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded-lg text-sm font-medium hover:bg-emerald-500/30 disabled:opacity-50 transition-colors"
                                            >
                                                {busyId === todo.id ? 'Processing...' : 'Approve'}
                                            </button>
                                            <button
                                                onClick={() => handleAction(todo.id, 'reject')}
                                                disabled={busyId === todo.id}
                                                className="px-4 py-2 bg-red-500/10 text-red-400 border border-red-500/30 rounded-lg text-sm font-medium hover:bg-red-500/20 disabled:opacity-50 transition-colors"
                                            >
                                                Reject
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </section>

                    <section className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6 opacity-75 hover:opacity-100 transition-opacity">
                        <h2 className="text-lg font-semibold text-white mb-4">Action History</h2>
                        {historyTodos.length === 0 ? (
                            <p className="text-slate-400">No completed actions yet.</p>
                        ) : (
                            <div className="space-y-3">
                                {historyTodos.map(todo => (
                                    <div key={todo.id} className="flex items-start justify-between border border-slate-700/40 rounded-lg p-4 bg-slate-900/20">
                                        <div>
                                            <div className="flex items-center gap-2 text-sm text-slate-400">
                                                <span className="font-mono">{todo.id.slice(0, 8)}</span>
                                                {todo.incident_id && (
                                                    <span className="text-slate-500">Incident {todo.incident_id.slice(0, 8)}</span>
                                                )}
                                            </div>
                                            <h3 className="text-white font-medium mt-1">{formatAction(todo.action_template)}</h3>
                                            <p className="text-slate-400 text-sm mt-1">{todo.target_resource}</p>
                                            {todo.result && (
                                                <p className="text-slate-500 text-xs mt-2">
                                                    Result: {todo.result.message || JSON.stringify(todo.result)}
                                                </p>
                                            )}
                                            {todo.error && (
                                                <p className="text-red-400 text-xs mt-2">Error: {todo.error}</p>
                                            )}
                                        </div>
                                        <div className="flex flex-col items-end gap-2">
                                            <StatusBadge status={todo.status} />
                                            {todo.completed_at && (
                                                <span className="text-xs text-slate-600">
                                                    {new Date(todo.completed_at).toLocaleTimeString()}
                                                </span>
                                            )}
                                        </div>
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
    return action.replace(/_/g, ' ').toUpperCase();
}

function StatusBadge({ status }: { status: string }) {
    const colors = {
        pending: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
        approved: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
        executing: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
        completed: 'bg-gray-500/20 text-gray-400 border-gray-500/30', // Completed successfully
        failed: 'bg-red-500/20 text-red-400 border-red-500/30',
        rejected: 'bg-red-900/20 text-red-500 border-red-900/30',
    };
    return (
        <span className={`px-3 py-1 rounded-full text-xs font-medium border ${colors[status as keyof typeof colors] || colors.pending} uppercase tracking-wider`}>
            {status}
        </span>
    );
}
