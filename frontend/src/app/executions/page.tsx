'use client';

import { useState, useEffect, useCallback } from 'react';
import { getApiUrl } from '@/lib/api-config';
import { 
    ExecutionTimeline, 
    buildTimelineEvents, 
    SafetyPolicyInfo,
    FilterBar,
    ActiveFilterPills,
    defaultFilters,
    PolicyDecisionBanner,
    PolicyDecisionSummary,
    PreviewModal,
    SkillSelectionStep,
    ParameterEntryStep,
    Pagination,
    type FilterState,
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

interface PreviewResponse {
    skill_id: string;
    skill_name: string;
    parameters: Record<string, unknown>;
    mode: string;
    risk_level: string;
    policy_decision: PolicyDecision;
    targets_affected: string[];
    estimated_duration_seconds: number;
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

const modeColors: Record<string, { bg: string; text: string; dot: string }> = {
    mock: { bg: 'bg-purple-500/20', text: 'text-purple-400', dot: 'bg-purple-400' },
    integration: { bg: 'bg-blue-500/20', text: 'text-blue-400', dot: 'bg-blue-400' },
    lab: { bg: 'bg-emerald-500/20', text: 'text-emerald-400', dot: 'bg-emerald-400' },
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

function ExecutionModeBadge({ executionMode }: { executionMode?: string }) {
    if (!executionMode) return null;
    const colors = modeColors[executionMode] || { bg: 'bg-slate-500/20', text: 'text-slate-400', dot: 'bg-slate-400' };
    return (
        <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium ${colors.bg} ${colors.text}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${colors.dot}`} />
            {executionMode}
        </span>
    );
}

type WizardStep = 'closed' | 'select_skill' | 'enter_params' | 'preview';

export default function ExecutionsPage() {
    const [executions, setExecutions] = useState<Execution[]>([]);
    const [skills, setSkills] = useState<Skill[]>([]);
    const [mode, setMode] = useState<ExecutionMode | null>(null);
    const [loading, setLoading] = useState(true);
    const [filters, setFilters] = useState<FilterState>(defaultFilters);
    const [selectedExecution, setSelectedExecution] = useState<Execution | null>(null);
    const [showPolicyInfo, setShowPolicyInfo] = useState(false);
    
    // Pagination state
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(20);
    const [total, setTotal] = useState(0);
    
    // Wizard state
    const [wizardStep, setWizardStep] = useState<WizardStep>('closed');
    const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null);
    const [skillParams, setSkillParams] = useState<Record<string, string>>({});
    const [preview, setPreview] = useState<PreviewResponse | null>(null);
    const [previewLoading, setPreviewLoading] = useState(false);

    // Build query string from filters and pagination
    const buildQueryString = useCallback(() => {
        const params = new URLSearchParams();
        if (filters.status !== 'all') params.set('status', filters.status);
        if (filters.risk !== 'all') params.set('risk', filters.risk);
        if (filters.mode !== 'all') params.set('mode', filters.mode);
        if (filters.skill_id) params.set('skill_id', filters.skill_id);
        if (filters.target) params.set('target', filters.target);
        if (filters.search) params.set('search', filters.search);
        if (filters.sort !== 'newest') params.set('sort', filters.sort);
        if (filters.needs_attention) params.set('needs_attention', 'true');
        // Pagination
        params.set('page', page.toString());
        params.set('page_size', pageSize.toString());
        return params.toString();
    }, [filters, page, pageSize]);

    const fetchData = useCallback(async () => {
        try {
            const queryString = buildQueryString();
            const [execRes, skillsRes, modeRes] = await Promise.all([
                fetch(getApiUrl(`/api/executions${queryString ? `?${queryString}` : ''}`)),
                fetch(getApiUrl('/api/executions/skills')),
                fetch(getApiUrl('/api/executions/mode')),
            ]);
            
            const execData = await execRes.json();
            const skillsData = await skillsRes.json();
            const modeData = await modeRes.json();
            
            setExecutions(execData.executions || []);
            setTotal(execData.total || 0);
            setSkills(skillsData.skills || []);
            setMode(modeData);
        } catch (err) {
            console.error('Failed to fetch data:', err);
        } finally {
            setLoading(false);
        }
    }, [buildQueryString]);

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 5000);
        return () => clearInterval(interval);
    }, [fetchData]);
    
    // Reset to page 1 when filters change
    const handleFiltersChange = useCallback((newFilters: FilterState) => {
        setFilters(newFilters);
        setPage(1); // Go back to first page on filter change
    }, []);
    
    // Pagination handlers
    const handlePageChange = useCallback((newPage: number) => {
        setPage(newPage);
    }, []);
    
    const handlePageSizeChange = useCallback((newSize: number) => {
        setPageSize(newSize);
        setPage(1); // Reset to first page when changing page size
    }, []);

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

    // Wizard handlers
    const openWizard = () => {
        setWizardStep('select_skill');
        setSelectedSkill(null);
        setSkillParams({});
        setPreview(null);
    };

    const closeWizard = () => {
        setWizardStep('closed');
        setSelectedSkill(null);
        setSkillParams({});
        setPreview(null);
    };

    const handleSelectSkill = (skill: Skill) => {
        setSelectedSkill(skill);
        setSkillParams({});
        setWizardStep('enter_params');
    };

    const handleRequestPreview = async () => {
        if (!selectedSkill) return;
        
        setWizardStep('preview');
        setPreviewLoading(true);
        
        try {
            const res = await fetch(getApiUrl('/api/executions/preview'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    skill_id: selectedSkill.id,
                    parameters: skillParams,
                }),
            });
            const data = await res.json();
            setPreview(data);
        } catch (err) {
            console.error('Failed to get preview:', err);
            setPreview(null);
        } finally {
            setPreviewLoading(false);
        }
    };

    const handleConfirmExecution = async () => {
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
            closeWizard();
            fetchData();
        } catch (err) {
            console.error('Failed to create execution:', err);
        }
    };

    // Count stats
    const pendingCount = executions.filter(e => e.status === 'pending_approval').length;

    return (
        <div className="space-y-6 max-w-6xl mx-auto">
            {/* Header */}
            <header className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white mb-2">Skill Executions</h1>
                    <p className="text-slate-400">
                        Manage and monitor skill execution lifecycle
                        {pendingCount > 0 && (
                            <span className="ml-2 px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 text-xs">
                                {pendingCount} pending
                            </span>
                        )}
                    </p>
                </div>
                <div className="flex items-center gap-4">
                    {mode && (
                        <button onClick={() => setShowPolicyInfo(!showPolicyInfo)}>
                            <ModeBadge mode={mode} />
                        </button>
                    )}
                    <button
                        onClick={openWizard}
                        className="px-4 py-2 bg-copilot-500 hover:bg-copilot-600 text-white rounded-lg font-medium transition-colors"
                    >
                        + New Execution
                    </button>
                </div>
            </header>

            {/* Safety Policy Info Panel */}
            {showPolicyInfo && mode && (
                <SafetyPolicyInfo mode={mode.mode as 'mock' | 'integration' | 'lab'} />
            )}

            {/* Filter Bar */}
            <FilterBar 
                filters={filters} 
                onChange={handleFiltersChange}
                skills={skills.map(s => ({ id: s.id, name: s.name }))}
            />

            {/* Active filter pills */}
            <ActiveFilterPills filters={filters} onChange={handleFiltersChange} />

            {/* Execution List */}
            {loading ? (
                <div className="text-slate-400 animate-pulse">Loading executions...</div>
            ) : executions.length === 0 ? (
                <div className="bg-slate-800/50 rounded-xl p-12 text-center border border-slate-700/50 backdrop-blur-sm">
                    <div className="text-5xl mb-6 opacity-80">📋</div>
                    <h3 className="text-xl font-medium text-white mb-2">No Executions</h3>
                    <p className="text-slate-400 mb-4">
                        {filters.status !== 'all' || filters.search 
                            ? 'No executions match your filters.' 
                            : 'Create a new skill execution to get started.'}
                    </p>
                    <button
                        onClick={openWizard}
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
                                    <div className="flex items-center gap-3 flex-wrap">
                                        <h3 className="text-lg font-bold text-white">
                                            {execution.skill_name}
                                        </h3>
                                        <StatusBadge status={execution.status} />
                                        <RiskBadge risk={execution.risk_level} />
                                        <ExecutionModeBadge executionMode={execution.execution_mode} />
                                    </div>
                                    <div className="flex items-center gap-3 text-sm text-slate-400">
                                        <span className="font-mono text-slate-500">{execution.id.slice(0, 8)}</span>
                                        <span>•</span>
                                        <span>{new Date(execution.created_at).toLocaleString()}</span>
                                        {execution.target_id && (
                                            <>
                                                <span>•</span>
                                                <span className="font-mono text-slate-500">
                                                    {execution.target_type}: {execution.target_id}
                                                </span>
                                            </>
                                        )}
                                    </div>
                                    {/* Policy decision summary */}
                                    {execution.policy_decision && (
                                        <PolicyDecisionSummary decision={execution.policy_decision} />
                                    )}
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
            
            {/* Pagination */}
            {!loading && total > 0 && (
                <Pagination
                    page={page}
                    pageSize={pageSize}
                    total={total}
                    onPageChange={handlePageChange}
                    onPageSizeChange={handlePageSizeChange}
                />
            )}

            {/* Creation Wizard - Step 1: Select Skill */}
            {wizardStep === 'select_skill' && (
                <SkillSelectionStep
                    skills={skills}
                    selectedSkill={selectedSkill}
                    onSelectSkill={handleSelectSkill}
                    onClose={closeWizard}
                />
            )}

            {/* Creation Wizard - Step 2: Enter Parameters */}
            {wizardStep === 'enter_params' && selectedSkill && (
                <ParameterEntryStep
                    skill={selectedSkill}
                    parameters={skillParams}
                    onChange={setSkillParams}
                    onBack={() => setWizardStep('select_skill')}
                    onPreview={handleRequestPreview}
                    onClose={closeWizard}
                />
            )}

            {/* Creation Wizard - Step 3: Preview */}
            {wizardStep === 'preview' && selectedSkill && (
                <PreviewModal
                    skill={selectedSkill}
                    parameters={skillParams}
                    preview={preview}
                    loading={previewLoading}
                    onClose={closeWizard}
                    onConfirm={handleConfirmExecution}
                    onBack={() => setWizardStep('enter_params')}
                />
            )}

            {/* Execution Details Modal */}
            {selectedExecution && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
                    <div className="bg-slate-800 rounded-2xl border border-slate-700 p-6 w-full max-w-3xl max-h-[85vh] overflow-auto">
                        <div className="flex items-center justify-between mb-6">
                            <div>
                                <h2 className="text-xl font-bold text-white">Execution Details</h2>
                                <p className="text-sm text-slate-400 font-mono">{selectedExecution.id}</p>
                            </div>
                            <button
                                onClick={() => setSelectedExecution(null)}
                                className="text-slate-400 hover:text-white"
                            >
                                ✕
                            </button>
                        </div>

                        {/* Mini-PR style layout */}
                        <div className="space-y-6">
                            {/* Summary header */}
                            <div className="flex items-center gap-4 p-4 bg-slate-700/30 rounded-xl">
                                <div className="flex-1">
                                    <h3 className="text-lg font-semibold text-white">{selectedExecution.skill_name}</h3>
                                    <div className="flex items-center gap-2 mt-1">
                                        <StatusBadge status={selectedExecution.status} />
                                        <RiskBadge risk={selectedExecution.risk_level} />
                                        <ExecutionModeBadge executionMode={selectedExecution.execution_mode} />
                                    </div>
                                </div>
                                {selectedExecution.target_id && (
                                    <div className="text-right">
                                        <p className="text-xs text-slate-500">Target</p>
                                        <p className="font-mono text-sm text-slate-300">
                                            {selectedExecution.target_type}: {selectedExecution.target_id}
                                        </p>
                                    </div>
                                )}
                            </div>

                            {/* Timeline section */}
                            <div>
                                <h4 className="text-sm font-medium text-slate-400 mb-3">Timeline</h4>
                                <ExecutionTimeline events={buildTimelineEvents(selectedExecution)} />
                            </div>

                            {/* Policy Decision section */}
                            {selectedExecution.policy_decision && (
                                <div>
                                    <h4 className="text-sm font-medium text-slate-400 mb-3">Policy Decision</h4>
                                    <PolicyDecisionBanner decision={selectedExecution.policy_decision} />
                                </div>
                            )}

                            {/* Parameters section */}
                            {Object.keys(selectedExecution.parameters).length > 0 && (
                                <div>
                                    <h4 className="text-sm font-medium text-slate-400 mb-3">Parameters</h4>
                                    <pre className="bg-slate-900/50 rounded-lg p-4 text-sm text-slate-300 overflow-auto font-mono">
                                        {JSON.stringify(selectedExecution.parameters, null, 2)}
                                    </pre>
                                </div>
                            )}

                            {/* Result section */}
                            {selectedExecution.result && (
                                <div>
                                    <h4 className="text-sm font-medium text-slate-400 mb-3">Result</h4>
                                    <div className={`p-4 rounded-xl border ${
                                        selectedExecution.result.success 
                                            ? 'bg-emerald-500/5 border-emerald-500/20' 
                                            : 'bg-red-500/5 border-red-500/20'
                                    }`}>
                                        <div className="flex items-center gap-3 mb-3">
                                            <span className={`text-lg ${selectedExecution.result.success ? 'text-emerald-400' : 'text-red-400'}`}>
                                                {selectedExecution.result.success ? '✓' : '✗'}
                                            </span>
                                            <span className={selectedExecution.result.success ? 'text-emerald-400' : 'text-red-400'}>
                                                {selectedExecution.result.success ? 'Success' : 'Failed'}
                                            </span>
                                            <span className="text-slate-500 text-sm">
                                                {selectedExecution.result.duration_ms}ms
                                            </span>
                                        </div>
                                        <pre className="bg-slate-900/50 rounded-lg p-3 text-sm text-slate-300 overflow-auto">
                                            {JSON.stringify(selectedExecution.result.output, null, 2)}
                                        </pre>
                                    </div>
                                </div>
                            )}

                            {/* Safety Warnings */}
                            {selectedExecution.result?.safety_warnings && selectedExecution.result.safety_warnings.length > 0 && (
                                <div>
                                    <h4 className="text-sm font-medium text-slate-400 mb-3">Safety Warnings</h4>
                                    <div className="space-y-2">
                                        {selectedExecution.result.safety_warnings.map((warning: string, index: number) => (
                                            <div key={index} className="flex items-start gap-2 text-sm bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2">
                                                <span className="text-amber-400">⚠</span>
                                                <span className="text-amber-200">{warning}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Rejection reason */}
                            {selectedExecution.rejection_reason && (
                                <div>
                                    <h4 className="text-sm font-medium text-slate-400 mb-3">Rejection</h4>
                                    <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4">
                                        <p className="text-red-400">{selectedExecution.rejection_reason}</p>
                                        {selectedExecution.rejected_by && (
                                            <p className="text-xs text-slate-500 mt-2">
                                                by {selectedExecution.rejected_by} at {new Date(selectedExecution.rejected_at!).toLocaleString()}
                                            </p>
                                        )}
                                    </div>
                                </div>
                            )}

                            {/* Error message */}
                            {selectedExecution.error_message && (
                                <div>
                                    <h4 className="text-sm font-medium text-slate-400 mb-3">Error</h4>
                                    <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4">
                                        <pre className="text-red-400 text-sm whitespace-pre-wrap font-mono">
                                            {selectedExecution.error_message}
                                        </pre>
                                    </div>
                                </div>
                            )}

                            {/* Audit info */}
                            <div>
                                <h4 className="text-sm font-medium text-slate-400 mb-3">Audit</h4>
                                <div className="grid grid-cols-2 gap-4 text-sm">
                                    <div>
                                        <span className="text-slate-500">Created:</span>
                                        <span className="text-slate-300 ml-2">{new Date(selectedExecution.created_at).toLocaleString()}</span>
                                    </div>
                                    <div>
                                        <span className="text-slate-500">Updated:</span>
                                        <span className="text-slate-300 ml-2">{new Date(selectedExecution.updated_at).toLocaleString()}</span>
                                    </div>
                                    {selectedExecution.approved_at && (
                                        <div>
                                            <span className="text-slate-500">Approved:</span>
                                            <span className="text-slate-300 ml-2">
                                                {new Date(selectedExecution.approved_at).toLocaleString()}
                                                {selectedExecution.approved_by && ` by ${selectedExecution.approved_by}`}
                                            </span>
                                        </div>
                                    )}
                                    {selectedExecution.executed_at && (
                                        <div>
                                            <span className="text-slate-500">Executed:</span>
                                            <span className="text-slate-300 ml-2">{new Date(selectedExecution.executed_at).toLocaleString()}</span>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
