'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getApiUrl } from '@/lib/api-config';
import { 
    ExecutionTimeline, 
    buildTimelineEvents, 
    PolicyDecisionBanner,
    PolicyFindingsList,
    ShareToolbar,
    type PolicyDecision,
} from '@/components/executions';

interface Execution {
    id: string;
    skill_id: string;
    skill_name: string;
    status: string;
    risk_level: string;
    execution_mode?: string;
    parameters: Record<string, unknown>;
    created_at: string;
    updated_at: string;
    approved_at?: string;
    approved_by?: string;
    rejected_at?: string;
    rejected_by?: string;
    rejection_reason?: string;
    executed_at?: string;
    target_type?: string;
    target_id?: string;
    policy_decision?: PolicyDecision;
    result?: {
        success: boolean;
        output: unknown;
        duration_ms: number;
        safety_warnings?: string[];
    };
    error_message?: string;
}

const statusColors: Record<string, { bg: string; text: string; border: string }> = {
    pending_approval: { bg: 'bg-amber-500/20', text: 'text-amber-400', border: 'border-amber-500/30' },
    approved: { bg: 'bg-blue-500/20', text: 'text-blue-400', border: 'border-blue-500/30' },
    rejected: { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/30' },
    completed: { bg: 'bg-emerald-500/20', text: 'text-emerald-400', border: 'border-emerald-500/30' },
    failed: { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/30' },
};

const riskColors: Record<string, { bg: string; text: string }> = {
    low: { bg: 'bg-emerald-500/20', text: 'text-emerald-400' },
    medium: { bg: 'bg-amber-500/20', text: 'text-amber-400' },
    high: { bg: 'bg-red-500/20', text: 'text-red-400' },
};

const modeColors: Record<string, { bg: string; text: string; icon: string }> = {
    mock: { bg: 'bg-purple-500/20', text: 'text-purple-400', icon: '🧪' },
    integration: { bg: 'bg-blue-500/20', text: 'text-blue-400', icon: '🔧' },
    lab: { bg: 'bg-emerald-500/20', text: 'text-emerald-400', icon: '🏠' },
};

type Tab = 'timeline' | 'parameters' | 'policy' | 'result' | 'audit';

export default function ExecutionDetailPage() {
    const params = useParams();
    const router = useRouter();
    const executionId = params.id as string;

    const [execution, setExecution] = useState<Execution | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<Tab>('timeline');

    const fetchExecution = useCallback(async () => {
        try {
            const res = await fetch(getApiUrl(`/api/executions/${executionId}`));
            if (!res.ok) {
                throw new Error('Execution not found');
            }
            const data = await res.json();
            setExecution(data);
            setError(null);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load execution');
        } finally {
            setLoading(false);
        }
    }, [executionId]);

    useEffect(() => {
        fetchExecution();
        // Auto-refresh for pending/approved executions
        const interval = setInterval(fetchExecution, 5000);
        return () => clearInterval(interval);
    }, [fetchExecution]);

    const handleApprove = async () => {
        try {
            await fetch(getApiUrl(`/api/executions/${executionId}/approve`), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ approved_by: 'operator' }),
            });
            fetchExecution();
        } catch (err) {
            console.error('Failed to approve:', err);
        }
    };

    const handleReject = async () => {
        const reason = prompt('Enter rejection reason:');
        if (!reason) return;
        
        try {
            await fetch(getApiUrl(`/api/executions/${executionId}/reject`), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ rejected_by: 'operator', reason }),
            });
            fetchExecution();
        } catch (err) {
            console.error('Failed to reject:', err);
        }
    };

    const handleExecute = async () => {
        try {
            await fetch(getApiUrl(`/api/executions/${executionId}/execute`), {
                method: 'POST',
            });
            fetchExecution();
        } catch (err) {
            console.error('Failed to execute:', err);
        }
    };

    if (loading) {
        return (
            <div className="max-w-4xl mx-auto py-12">
                <div className="animate-pulse space-y-4">
                    <div className="h-8 bg-slate-700/50 rounded w-1/3" />
                    <div className="h-4 bg-slate-700/50 rounded w-1/4" />
                    <div className="h-32 bg-slate-700/50 rounded" />
                </div>
            </div>
        );
    }

    if (error || !execution) {
        return (
            <div className="max-w-4xl mx-auto py-12 text-center">
                <div className="text-6xl mb-4">🔍</div>
                <h1 className="text-2xl font-bold text-white mb-2">Execution Not Found</h1>
                <p className="text-slate-400 mb-6">{error || 'The requested execution could not be found.'}</p>
                <button
                    onClick={() => router.push('/executions')}
                    className="px-4 py-2 bg-copilot-500 hover:bg-copilot-600 text-white rounded-lg transition-colors"
                >
                    ← Back to Executions
                </button>
            </div>
        );
    }

    const status = statusColors[execution.status] || statusColors.pending_approval;
    const risk = riskColors[execution.risk_level] || riskColors.medium;
    const mode = execution.execution_mode ? modeColors[execution.execution_mode] : null;

    const tabs: Array<{ id: Tab; label: string; show: boolean }> = [
        { id: 'timeline', label: 'Timeline', show: true },
        { id: 'parameters', label: 'Inputs', show: Object.keys(execution.parameters).length > 0 },
        { id: 'policy', label: 'Policy', show: !!execution.policy_decision },
        { id: 'result', label: 'Result', show: !!execution.result },
        { id: 'audit', label: 'Audit', show: true },
    ];

    return (
        <div className="max-w-4xl mx-auto space-y-6">
            {/* Back button */}
            <button
                onClick={() => router.push('/executions')}
                className="text-slate-400 hover:text-white text-sm flex items-center gap-1 transition-colors"
            >
                ← Back to Executions
            </button>

            {/* PR-style Header */}
            <div className="bg-slate-800/50 border border-slate-700/50 rounded-2xl overflow-hidden">
                {/* Title bar */}
                <div className="p-6 border-b border-slate-700/50">
                    <div className="flex items-start justify-between">
                        <div>
                            <h1 className="text-2xl font-bold text-white mb-2">
                                {execution.skill_name}
                            </h1>
                            <div className="flex items-center gap-3 flex-wrap">
                                <span className={`px-3 py-1 rounded-full text-sm font-medium border ${status.bg} ${status.text} ${status.border}`}>
                                    {execution.status.replace('_', ' ')}
                                </span>
                                <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${risk.bg} ${risk.text}`}>
                                    {execution.risk_level} risk
                                </span>
                                {mode && (
                                    <span className={`px-2.5 py-1 rounded-lg text-xs font-medium ${mode.bg} ${mode.text}`}>
                                        {mode.icon} {execution.execution_mode}
                                    </span>
                                )}
                            </div>
                        </div>
                        
                        {/* Action buttons */}
                        <div className="flex items-center gap-2">
                            {execution.status === 'pending_approval' && (
                                <>
                                    <button
                                        onClick={handleApprove}
                                        className="px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg font-medium transition-colors"
                                    >
                                        ✓ Approve
                                    </button>
                                    <button
                                        onClick={handleReject}
                                        className="px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg font-medium transition-colors"
                                    >
                                        ✗ Reject
                                    </button>
                                </>
                            )}
                            {execution.status === 'approved' && (
                                <button
                                    onClick={handleExecute}
                                    className="px-4 py-2 bg-copilot-500 hover:bg-copilot-600 text-white rounded-lg font-medium transition-colors"
                                >
                                    ▶ Execute
                                </button>
                            )}
                        </div>
                    </div>
                    
                    {/* Metadata line */}
                    <div className="flex items-center justify-between mt-4">
                        <div className="flex items-center gap-4 text-sm text-slate-400">
                            <span className="font-mono">{execution.id.slice(0, 12)}...</span>
                            <span>•</span>
                            <span>Created {new Date(execution.created_at).toLocaleString()}</span>
                            {execution.target_id && (
                                <>
                                    <span>•</span>
                                    <span className="font-mono text-slate-300">
                                        {execution.target_type}: {execution.target_id}
                                    </span>
                                </>
                            )}
                        </div>
                        
                        {/* Copy + Share toolbar */}
                        <ShareToolbar 
                            executionId={execution.id}
                            policyDecision={execution.policy_decision}
                            fullData={execution}
                        />
                    </div>
                </div>

                {/* Tab navigation */}
                <div className="border-b border-slate-700/50">
                    <div className="flex gap-1 px-4">
                        {tabs.filter(t => t.show).map((tab) => (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={`px-4 py-3 text-sm font-medium transition-colors border-b-2 -mb-px ${
                                    activeTab === tab.id
                                        ? 'text-copilot-400 border-copilot-400'
                                        : 'text-slate-400 border-transparent hover:text-white'
                                }`}
                            >
                                {tab.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Tab content */}
                <div className="p-6">
                    {/* Timeline Tab */}
                    {activeTab === 'timeline' && (
                        <div className="space-y-6">
                            <ExecutionTimeline events={buildTimelineEvents(execution)} />
                            
                            {/* Quick status info */}
                            {execution.status === 'pending_approval' && (
                                <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl">
                                    <p className="text-amber-400 font-medium mb-1">Awaiting Approval</p>
                                    <p className="text-sm text-slate-400">
                                        This execution requires operator approval before it can be executed.
                                    </p>
                                </div>
                            )}
                            
                            {execution.rejection_reason && (
                                <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl">
                                    <p className="text-red-400 font-medium mb-1">Rejected</p>
                                    <p className="text-sm text-slate-300">{execution.rejection_reason}</p>
                                    {execution.rejected_by && (
                                        <p className="text-xs text-slate-500 mt-2">
                                            by {execution.rejected_by} at {new Date(execution.rejected_at!).toLocaleString()}
                                        </p>
                                    )}
                                </div>
                            )}
                            
                            {execution.error_message && (
                                <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl">
                                    <p className="text-red-400 font-medium mb-2">Execution Error</p>
                                    <pre className="text-sm text-red-300 font-mono whitespace-pre-wrap">
                                        {execution.error_message}
                                    </pre>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Parameters Tab */}
                    {activeTab === 'parameters' && (
                        <div className="space-y-4">
                            <h3 className="text-sm font-medium text-slate-400">Input Parameters</h3>
                            <div className="bg-slate-900/50 rounded-xl p-4 font-mono text-sm">
                                {Object.entries(execution.parameters).map(([key, value]) => (
                                    <div key={key} className="flex py-2 border-b border-slate-700/30 last:border-0">
                                        <span className="w-32 flex-shrink-0 text-slate-500">{key}</span>
                                        <span className="text-slate-300">{JSON.stringify(value)}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Policy Tab */}
                    {activeTab === 'policy' && execution.policy_decision && (
                        <div className="space-y-6">
                            <PolicyDecisionBanner decision={execution.policy_decision} />
                            
                            {execution.policy_decision.findings.length > 0 && (
                                <div>
                                    <h4 className="text-sm font-medium text-slate-400 mb-3">All Findings</h4>
                                    <PolicyFindingsList 
                                        findings={execution.policy_decision.findings}
                                    />
                                </div>
                            )}
                        </div>
                    )}

                    {/* Result Tab */}
                    {activeTab === 'result' && execution.result && (
                        <div className="space-y-6">
                            {/* Result summary */}
                            <div className={`p-6 rounded-xl border ${
                                execution.result.success 
                                    ? 'bg-emerald-500/5 border-emerald-500/20' 
                                    : 'bg-red-500/5 border-red-500/20'
                            }`}>
                                <div className="flex items-center gap-4 mb-4">
                                    <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                                        execution.result.success ? 'bg-emerald-500/20' : 'bg-red-500/20'
                                    }`}>
                                        <span className={`text-2xl ${execution.result.success ? 'text-emerald-400' : 'text-red-400'}`}>
                                            {execution.result.success ? '✓' : '✗'}
                                        </span>
                                    </div>
                                    <div>
                                        <h3 className={`text-lg font-semibold ${execution.result.success ? 'text-emerald-400' : 'text-red-400'}`}>
                                            {execution.result.success ? 'Execution Successful' : 'Execution Failed'}
                                        </h3>
                                        <p className="text-sm text-slate-400">
                                            Duration: {execution.result.duration_ms}ms
                                        </p>
                                    </div>
                                </div>

                                <div>
                                    <h4 className="text-sm font-medium text-slate-400 mb-2">Output</h4>
                                    <pre className="bg-slate-900/50 rounded-lg p-4 text-sm text-slate-300 overflow-auto max-h-96 font-mono">
                                        {JSON.stringify(execution.result.output, null, 2)}
                                    </pre>
                                </div>
                            </div>

                            {/* Safety Warnings */}
                            {execution.result.safety_warnings && execution.result.safety_warnings.length > 0 && (
                                <div>
                                    <h4 className="text-sm font-medium text-slate-400 mb-3">Safety Warnings</h4>
                                    <div className="space-y-2">
                                        {execution.result.safety_warnings.map((warning, index) => (
                                            <div key={index} className="flex items-start gap-3 p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                                                <span className="text-amber-400 text-lg">⚠</span>
                                                <span className="text-amber-200">{warning}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Audit Tab */}
                    {activeTab === 'audit' && (
                        <div className="space-y-6">
                            <div className="grid grid-cols-2 gap-6">
                                <div className="space-y-4">
                                    <h4 className="text-sm font-medium text-slate-400">Identifiers</h4>
                                    <div className="space-y-3">
                                        <div>
                                            <span className="text-xs text-slate-500 block">Execution ID</span>
                                            <span className="text-sm text-slate-300 font-mono">{execution.id}</span>
                                        </div>
                                        <div>
                                            <span className="text-xs text-slate-500 block">Skill ID</span>
                                            <span className="text-sm text-slate-300 font-mono">{execution.skill_id}</span>
                                        </div>
                                        {execution.target_id && (
                                            <div>
                                                <span className="text-xs text-slate-500 block">Target</span>
                                                <span className="text-sm text-slate-300 font-mono">
                                                    {execution.target_type}: {execution.target_id}
                                                </span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                                
                                <div className="space-y-4">
                                    <h4 className="text-sm font-medium text-slate-400">Timestamps</h4>
                                    <div className="space-y-3">
                                        <div>
                                            <span className="text-xs text-slate-500 block">Created</span>
                                            <span className="text-sm text-slate-300">{new Date(execution.created_at).toLocaleString()}</span>
                                        </div>
                                        <div>
                                            <span className="text-xs text-slate-500 block">Updated</span>
                                            <span className="text-sm text-slate-300">{new Date(execution.updated_at).toLocaleString()}</span>
                                        </div>
                                        {execution.approved_at && (
                                            <div>
                                                <span className="text-xs text-slate-500 block">Approved</span>
                                                <span className="text-sm text-slate-300">
                                                    {new Date(execution.approved_at).toLocaleString()}
                                                    {execution.approved_by && ` by ${execution.approved_by}`}
                                                </span>
                                            </div>
                                        )}
                                        {execution.rejected_at && (
                                            <div>
                                                <span className="text-xs text-slate-500 block">Rejected</span>
                                                <span className="text-sm text-slate-300">
                                                    {new Date(execution.rejected_at).toLocaleString()}
                                                    {execution.rejected_by && ` by ${execution.rejected_by}`}
                                                </span>
                                            </div>
                                        )}
                                        {execution.executed_at && (
                                            <div>
                                                <span className="text-xs text-slate-500 block">Executed</span>
                                                <span className="text-sm text-slate-300">{new Date(execution.executed_at).toLocaleString()}</span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>

                            {/* Raw JSON export */}
                            <div className="pt-6 border-t border-slate-700/50">
                                <details>
                                    <summary className="text-sm text-slate-400 cursor-pointer hover:text-white">
                                        View Raw JSON
                                    </summary>
                                    <pre className="mt-3 bg-slate-900/50 rounded-lg p-4 text-xs text-slate-400 overflow-auto max-h-64 font-mono">
                                        {JSON.stringify(execution, null, 2)}
                                    </pre>
                                </details>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
