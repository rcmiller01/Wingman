'use client';

import { useState, useEffect, useCallback } from 'react';
import { getApiUrl } from '@/lib/api-config';

interface Execution {
    id: string;
    skill_id: string;
    skill_name: string;
    status: string;
    risk_level: string;
    parameters: Record<string, unknown>;
    created_at: string;
    updated_at: string;
    approved_at?: string;
    approved_by?: string;
    rejected_at?: string;
    rejected_by?: string;
    rejection_reason?: string;
    executed_at?: string;
    result?: {
        success: boolean;
        output: unknown;
        duration_ms: number;
    };
    error_message?: string;
}

interface ExecutionMode {
    mode: string;
    is_mock: boolean;
    is_integration: boolean;
    is_lab: boolean;
    should_execute_real: boolean;
}

interface Skill {
    id: string;
    name: string;
    description: string;
    category: string;
    risk: string;
    target_types: string[];
    required_params: string[];
    optional_params: string[];
    estimated_duration_seconds: number;
    tags: string[];
    requires_confirmation: boolean;
}

const statusColors: Record<string, string> = {
    pending_approval: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    approved: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    rejected: 'bg-red-500/20 text-red-400 border-red-500/30',
    completed: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    failed: 'bg-red-500/20 text-red-400 border-red-500/30',
};

const riskColors: Record<string, string> = {
    low: 'bg-emerald-500/20 text-emerald-400',
    medium: 'bg-amber-500/20 text-amber-400',
    high: 'bg-red-500/20 text-red-400',
};

function StatusBadge({ status }: { status: string }) {
    const colors = statusColors[status] || 'bg-slate-500/20 text-slate-400';
    return (
        <span className={`px-2 py-1 rounded-full text-xs font-medium border ${colors}`}>
            {status.replace('_', ' ')}
        </span>
    );
}

function RiskBadge({ risk }: { risk: string }) {
    const colors = riskColors[risk] || 'bg-slate-500/20 text-slate-400';
    return (
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors}`}>
            {risk}
        </span>
    );
}

function ModeBadge({ mode }: { mode: ExecutionMode }) {
    if (mode.is_mock) {
        return (
            <div className="flex items-center gap-2 px-3 py-1 bg-purple-500/20 text-purple-400 rounded-lg text-sm">
                <span className="w-2 h-2 rounded-full bg-purple-400 animate-pulse" />
                Mock Mode
            </div>
        );
    }
    if (mode.is_integration) {
        return (
            <div className="flex items-center gap-2 px-3 py-1 bg-blue-500/20 text-blue-400 rounded-lg text-sm">
                <span className="w-2 h-2 rounded-full bg-blue-400" />
                Integration Mode
            </div>
        );
    }
    return (
        <div className="flex items-center gap-2 px-3 py-1 bg-emerald-500/20 text-emerald-400 rounded-lg text-sm">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            Lab Mode (Live)
        </div>
    );
}

export default function ExecutionsPage() {
    const [executions, setExecutions] = useState<Execution[]>([]);
    const [skills, setSkills] = useState<Skill[]>([]);
    const [mode, setMode] = useState<ExecutionMode | null>(null);
    const [loading, setLoading] = useState(true);
    const [statusFilter, setStatusFilter] = useState<string>('all');
    const [selectedExecution, setSelectedExecution] = useState<Execution | null>(null);
    const [showSkillModal, setShowSkillModal] = useState(false);
    const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null);
    const [skillParams, setSkillParams] = useState<Record<string, string>>({});

    const fetchData = useCallback(async () => {
        try {
            const statusParam = statusFilter === 'all' ? '' : `?status=${statusFilter}`;
            const [execRes, skillsRes, modeRes] = await Promise.all([
                fetch(getApiUrl(`/api/executions${statusParam}`)),
                fetch(getApiUrl('/api/executions/skills')),
                fetch(getApiUrl('/api/executions/mode')),
            ]);
            
            const execData = await execRes.json();
            const skillsData = await skillsRes.json();
            const modeData = await modeRes.json();
            
            setExecutions(execData.executions || []);
            setSkills(skillsData.skills || []);
            setMode(modeData);
        } catch (err) {
            console.error('Failed to fetch data:', err);
        } finally {
            setLoading(false);
        }
    }, [statusFilter]);

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 5000);
        return () => clearInterval(interval);
    }, [fetchData]);

    const handleApprove = async (executionId: string) => {
        try {
            await fetch(getApiUrl(`/api/executions/${executionId}/approve`), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ approved_by: 'operator' }),
            });
            fetchData();
        } catch (err) {
            console.error('Failed to approve:', err);
        }
    };

    const handleReject = async (executionId: string, reason: string) => {
        try {
            await fetch(getApiUrl(`/api/executions/${executionId}/reject`), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ rejected_by: 'operator', reason }),
            });
            fetchData();
        } catch (err) {
            console.error('Failed to reject:', err);
        }
    };

    const handleExecute = async (executionId: string) => {
        try {
            await fetch(getApiUrl(`/api/executions/${executionId}/execute`), {
                method: 'POST',
            });
            fetchData();
        } catch (err) {
            console.error('Failed to execute:', err);
        }
    };

    const handleCreateExecution = async () => {
        if (!selectedSkill) return;
        
        try {
            await fetch(getApiUrl('/api/executions'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    skill_id: selectedSkill.id,
                    parameters: skillParams,
                }),
            });
            setShowSkillModal(false);
            setSelectedSkill(null);
            setSkillParams({});
            fetchData();
        } catch (err) {
            console.error('Failed to create execution:', err);
        }
    };

    return (
        <div className="space-y-6 max-w-6xl mx-auto">
            {/* Header */}
            <header className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white mb-2">Skill Executions</h1>
                    <p className="text-slate-400">Manage and monitor skill execution lifecycle</p>
                </div>
                <div className="flex items-center gap-4">
                    {mode && <ModeBadge mode={mode} />}
                    <button
                        onClick={() => setShowSkillModal(true)}
                        className="px-4 py-2 bg-copilot-500 hover:bg-copilot-600 text-white rounded-lg font-medium transition-colors"
                    >
                        + New Execution
                    </button>
                </div>
            </header>

            {/* Filters */}
            <div className="flex gap-2">
                {['all', 'pending_approval', 'approved', 'completed', 'rejected', 'failed'].map((status) => (
                    <button
                        key={status}
                        onClick={() => setStatusFilter(status)}
                        className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                            statusFilter === status
                                ? 'bg-copilot-500/20 text-copilot-400 border border-copilot-500/30'
                                : 'bg-slate-800/50 text-slate-400 border border-slate-700/50 hover:border-slate-600'
                        }`}
                    >
                        {status === 'all' ? 'All' : status.replace('_', ' ')}
                    </button>
                ))}
            </div>

            {/* Execution List */}
            {loading ? (
                <div className="text-slate-400 animate-pulse">Loading executions...</div>
            ) : executions.length === 0 ? (
                <div className="bg-slate-800/50 rounded-xl p-12 text-center border border-slate-700/50 backdrop-blur-sm">
                    <div className="text-5xl mb-6 opacity-80">📋</div>
                    <h3 className="text-xl font-medium text-white mb-2">No Executions</h3>
                    <p className="text-slate-400 mb-4">Create a new skill execution to get started.</p>
                    <button
                        onClick={() => setShowSkillModal(true)}
                        className="px-4 py-2 bg-copilot-500 hover:bg-copilot-600 text-white rounded-lg font-medium transition-colors"
                    >
                        + New Execution
                    </button>
                </div>
            ) : (
                <div className="space-y-4">
                    {executions.map((execution) => (
                        <div
                            key={execution.id}
                            className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6 hover:border-slate-600 transition-colors"
                        >
                            <div className="flex items-start justify-between mb-4">
                                <div className="space-y-2">
                                    <div className="flex items-center gap-3">
                                        <h3 className="text-lg font-bold text-white">
                                            {execution.skill_name}
                                        </h3>
                                        <StatusBadge status={execution.status} />
                                        <RiskBadge risk={execution.risk_level} />
                                    </div>
                                    <div className="text-sm text-slate-400">
                                        <span className="font-mono text-slate-500">{execution.id.slice(0, 8)}</span>
                                        <span className="mx-2">•</span>
                                        <span>{new Date(execution.created_at).toLocaleString()}</span>
                                    </div>
                                </div>
                                
                                {/* Action Buttons */}
                                <div className="flex gap-2">
                                    {execution.status === 'pending_approval' && (
                                        <>
                                            <button
                                                onClick={() => handleApprove(execution.id)}
                                                className="px-3 py-1.5 bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 rounded-lg text-sm font-medium transition-colors"
                                            >
                                                ✓ Approve
                                            </button>
                                            <button
                                                onClick={() => handleReject(execution.id, 'Manually rejected')}
                                                className="px-3 py-1.5 bg-red-500/20 text-red-400 hover:bg-red-500/30 rounded-lg text-sm font-medium transition-colors"
                                            >
                                                ✗ Reject
                                            </button>
                                        </>
                                    )}
                                    {execution.status === 'approved' && (
                                        <button
                                            onClick={() => handleExecute(execution.id)}
                                            className="px-3 py-1.5 bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 rounded-lg text-sm font-medium transition-colors"
                                        >
                                            ▶ Execute
                                        </button>
                                    )}
                                    <button
                                        onClick={() => setSelectedExecution(execution)}
                                        className="px-3 py-1.5 bg-slate-700/50 text-slate-300 hover:bg-slate-700 rounded-lg text-sm font-medium transition-colors"
                                    >
                                        Details
                                    </button>
                                </div>
                            </div>

                            {/* Parameters */}
                            {Object.keys(execution.parameters).length > 0 && (
                                <div className="text-sm text-slate-400 bg-slate-900/50 rounded-lg p-3 font-mono">
                                    {Object.entries(execution.parameters).map(([key, value]) => (
                                        <div key={key}>
                                            <span className="text-slate-500">{key}:</span>{' '}
                                            <span className="text-slate-300">{String(value)}</span>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Result (if completed) */}
                            {execution.result && (
                                <div className="mt-4 text-sm">
                                    <div className="flex items-center gap-2 mb-2">
                                        <span className={execution.result.success ? 'text-emerald-400' : 'text-red-400'}>
                                            {execution.result.success ? '✓ Success' : '✗ Failed'}
                                        </span>
                                        <span className="text-slate-500">
                                            ({execution.result.duration_ms}ms)
                                        </span>
                                    </div>
                                    <pre className="bg-slate-900/50 rounded-lg p-3 text-slate-300 overflow-auto max-h-40">
                                        {JSON.stringify(execution.result.output, null, 2)}
                                    </pre>
                                </div>
                            )}

                            {/* Rejection reason */}
                            {execution.rejection_reason && (
                                <div className="mt-4 text-sm bg-red-500/10 rounded-lg p-3 border border-red-500/20">
                                    <span className="text-red-400">Rejected:</span>{' '}
                                    <span className="text-slate-300">{execution.rejection_reason}</span>
                                </div>
                            )}

                            {/* Error message */}
                            {execution.error_message && (
                                <div className="mt-4 text-sm bg-red-500/10 rounded-lg p-3 border border-red-500/20">
                                    <span className="text-red-400">Error:</span>{' '}
                                    <span className="text-slate-300">{execution.error_message}</span>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {/* Skill Selection Modal */}
            {showSkillModal && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
                    <div className="bg-slate-800 rounded-2xl border border-slate-700 p-6 w-full max-w-2xl max-h-[80vh] overflow-auto">
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-xl font-bold text-white">Select Skill to Execute</h2>
                            <button
                                onClick={() => {
                                    setShowSkillModal(false);
                                    setSelectedSkill(null);
                                    setSkillParams({});
                                }}
                                className="text-slate-400 hover:text-white"
                            >
                                ✕
                            </button>
                        </div>

                        {!selectedSkill ? (
                            <div className="space-y-3">
                                {skills.map((skill) => (
                                    <button
                                        key={skill.id}
                                        onClick={() => setSelectedSkill(skill)}
                                        className="w-full text-left bg-slate-700/50 hover:bg-slate-700 rounded-xl p-4 transition-colors"
                                    >
                                        <div className="flex items-center justify-between mb-2">
                                            <span className="font-semibold text-white">{skill.name}</span>
                                            <div className="flex gap-2">
                                                <span className="px-2 py-0.5 rounded text-xs bg-slate-600 text-slate-300">
                                                    {skill.category}
                                                </span>
                                                <RiskBadge risk={skill.risk} />
                                            </div>
                                        </div>
                                        <p className="text-sm text-slate-400">{skill.description}</p>
                                    </button>
                                ))}
                            </div>
                        ) : (
                            <div className="space-y-4">
                                <div className="bg-slate-700/50 rounded-xl p-4">
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="font-semibold text-white">{selectedSkill.name}</span>
                                        <button
                                            onClick={() => {
                                                setSelectedSkill(null);
                                                setSkillParams({});
                                            }}
                                            className="text-sm text-copilot-400 hover:text-copilot-300"
                                        >
                                            Change
                                        </button>
                                    </div>
                                    <p className="text-sm text-slate-400">{selectedSkill.description}</p>
                                </div>

                                {/* Required Parameters */}
                                {selectedSkill.required_params.length > 0 && (
                                    <div className="space-y-3">
                                        <h3 className="text-sm font-medium text-slate-400">Required Parameters</h3>
                                        {selectedSkill.required_params.map((param) => (
                                            <div key={param}>
                                                <label className="block text-sm text-slate-300 mb-1">{param}</label>
                                                <input
                                                    type="text"
                                                    value={skillParams[param] || ''}
                                                    onChange={(e) => setSkillParams({ ...skillParams, [param]: e.target.value })}
                                                    className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-3 py-2 text-white focus:border-copilot-500 focus:outline-none"
                                                    placeholder={`Enter ${param}`}
                                                />
                                            </div>
                                        ))}
                                    </div>
                                )}

                                {/* Optional Parameters */}
                                {selectedSkill.optional_params.length > 0 && (
                                    <div className="space-y-3">
                                        <h3 className="text-sm font-medium text-slate-400">Optional Parameters</h3>
                                        {selectedSkill.optional_params.map((param) => (
                                            <div key={param}>
                                                <label className="block text-sm text-slate-300 mb-1">{param}</label>
                                                <input
                                                    type="text"
                                                    value={skillParams[param] || ''}
                                                    onChange={(e) => setSkillParams({ ...skillParams, [param]: e.target.value })}
                                                    className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-3 py-2 text-white focus:border-copilot-500 focus:outline-none"
                                                    placeholder={`Enter ${param} (optional)`}
                                                />
                                            </div>
                                        ))}
                                    </div>
                                )}

                                <button
                                    onClick={handleCreateExecution}
                                    disabled={selectedSkill.required_params.some((p) => !skillParams[p])}
                                    className="w-full mt-4 px-4 py-3 bg-copilot-500 hover:bg-copilot-600 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded-lg font-medium transition-colors"
                                >
                                    Create Execution Request
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Execution Details Modal */}
            {selectedExecution && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
                    <div className="bg-slate-800 rounded-2xl border border-slate-700 p-6 w-full max-w-2xl max-h-[80vh] overflow-auto">
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-xl font-bold text-white">Execution Details</h2>
                            <button
                                onClick={() => setSelectedExecution(null)}
                                className="text-slate-400 hover:text-white"
                            >
                                ✕
                            </button>
                        </div>

                        <div className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <span className="text-sm text-slate-400">ID</span>
                                    <p className="text-white font-mono text-sm">{selectedExecution.id}</p>
                                </div>
                                <div>
                                    <span className="text-sm text-slate-400">Skill</span>
                                    <p className="text-white">{selectedExecution.skill_name}</p>
                                </div>
                                <div>
                                    <span className="text-sm text-slate-400">Status</span>
                                    <div className="mt-1">
                                        <StatusBadge status={selectedExecution.status} />
                                    </div>
                                </div>
                                <div>
                                    <span className="text-sm text-slate-400">Risk Level</span>
                                    <div className="mt-1">
                                        <RiskBadge risk={selectedExecution.risk_level} />
                                    </div>
                                </div>
                            </div>

                            <div>
                                <span className="text-sm text-slate-400">Timeline</span>
                                <div className="mt-2 space-y-2 text-sm">
                                    <div className="flex items-center gap-2">
                                        <span className="w-24 text-slate-500">Created:</span>
                                        <span className="text-white">{new Date(selectedExecution.created_at).toLocaleString()}</span>
                                    </div>
                                    {selectedExecution.approved_at && (
                                        <div className="flex items-center gap-2">
                                            <span className="w-24 text-slate-500">Approved:</span>
                                            <span className="text-emerald-400">{new Date(selectedExecution.approved_at).toLocaleString()}</span>
                                            <span className="text-slate-500">by {selectedExecution.approved_by}</span>
                                        </div>
                                    )}
                                    {selectedExecution.rejected_at && (
                                        <div className="flex items-center gap-2">
                                            <span className="w-24 text-slate-500">Rejected:</span>
                                            <span className="text-red-400">{new Date(selectedExecution.rejected_at).toLocaleString()}</span>
                                            <span className="text-slate-500">by {selectedExecution.rejected_by}</span>
                                        </div>
                                    )}
                                    {selectedExecution.executed_at && (
                                        <div className="flex items-center gap-2">
                                            <span className="w-24 text-slate-500">Executed:</span>
                                            <span className="text-blue-400">{new Date(selectedExecution.executed_at).toLocaleString()}</span>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {Object.keys(selectedExecution.parameters).length > 0 && (
                                <div>
                                    <span className="text-sm text-slate-400">Parameters</span>
                                    <pre className="mt-2 bg-slate-900/50 rounded-lg p-3 text-sm text-slate-300 overflow-auto">
                                        {JSON.stringify(selectedExecution.parameters, null, 2)}
                                    </pre>
                                </div>
                            )}

                            {selectedExecution.result && (
                                <div>
                                    <span className="text-sm text-slate-400">Result</span>
                                    <pre className="mt-2 bg-slate-900/50 rounded-lg p-3 text-sm text-slate-300 overflow-auto">
                                        {JSON.stringify(selectedExecution.result, null, 2)}
                                    </pre>
                                </div>
                            )}

                            {selectedExecution.rejection_reason && (
                                <div>
                                    <span className="text-sm text-slate-400">Rejection Reason</span>
                                    <p className="mt-1 text-red-400">{selectedExecution.rejection_reason}</p>
                                </div>
                            )}

                            {selectedExecution.error_message && (
                                <div>
                                    <span className="text-sm text-slate-400">Error Message</span>
                                    <p className="mt-1 text-red-400">{selectedExecution.error_message}</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
