'use client';

import React, { useState, useEffect } from 'react';
import { getApiUrl } from '@/lib/api-config';

interface AllowlistEntry {
    pattern: string;
    type: 'exact' | 'regex';
    source: string;
}

interface AllowlistInfo {
    name: string;
    env_var: string;
    entries: AllowlistEntry[];
    count: number;
    is_empty: boolean;
}

interface SafetyModeInfo {
    mode: string;
    is_mock: boolean;
    is_integration: boolean;
    is_lab: boolean;
    description: string;
    dangerous_ok: boolean;
    read_only: boolean;
    prune_enabled: boolean;
}

interface SafetyStatus {
    mode: SafetyModeInfo;
    allowlists: AllowlistInfo[];
    warnings: string[];
}

interface TargetCheckResult {
    allowed: boolean;
    reason: string;
    matched_allowlist?: string;
    matched_pattern?: string;
    suggestions: string[];
}

const modeColors = {
    mock: { bg: 'bg-purple-500/20', text: 'text-purple-400', border: 'border-purple-500/30', dot: 'bg-purple-400' },
    integration: { bg: 'bg-blue-500/20', text: 'text-blue-400', border: 'border-blue-500/30', dot: 'bg-blue-400' },
    lab: { bg: 'bg-emerald-500/20', text: 'text-emerald-400', border: 'border-emerald-500/30', dot: 'bg-emerald-400' },
};

export function SafetyStatusPanel() {
    const [status, setStatus] = useState<SafetyStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [expanded, setExpanded] = useState(false);
    
    // Target check state
    const [checkTarget, setCheckTarget] = useState({ type: 'docker', id: '', operation: 'access' });
    const [checkResult, setCheckResult] = useState<TargetCheckResult | null>(null);
    const [checkLoading, setCheckLoading] = useState(false);

    useEffect(() => {
        const fetchStatus = async () => {
            try {
                const res = await fetch(getApiUrl('/api/safety/status'));
                if (!res.ok) throw new Error('Failed to fetch safety status');
                const data = await res.json();
                setStatus(data);
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Failed to load');
            } finally {
                setLoading(false);
            }
        };
        
        fetchStatus();
    }, []);

    const handleCheckTarget = async () => {
        if (!checkTarget.id.trim()) return;
        
        setCheckLoading(true);
        setCheckResult(null);
        
        try {
            const res = await fetch(getApiUrl('/api/safety/check-target'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    target_type: checkTarget.type,
                    target_id: checkTarget.id.trim(),
                    operation: checkTarget.operation,
                }),
            });
            
            if (!res.ok) throw new Error('Check failed');
            const data = await res.json();
            setCheckResult(data);
        } catch (err) {
            setCheckResult({
                allowed: false,
                reason: 'Failed to check target',
                suggestions: [],
            });
        } finally {
            setCheckLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50 animate-pulse">
                <div className="h-6 bg-slate-700 rounded w-1/3"></div>
            </div>
        );
    }

    if (error || !status) {
        return (
            <div className="bg-red-500/10 rounded-xl p-4 border border-red-500/20 text-red-400">
                ⚠️ Failed to load safety status: {error}
            </div>
        );
    }

    const modeStyle = modeColors[status.mode.mode as keyof typeof modeColors] || modeColors.mock;

    return (
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden">
            {/* Header - Always visible */}
            <div 
                className="p-4 cursor-pointer hover:bg-slate-800/70 transition-colors"
                onClick={() => setExpanded(!expanded)}
            >
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${modeStyle.bg} ${modeStyle.text} border ${modeStyle.border}`}>
                            <span className={`w-2 h-2 rounded-full ${modeStyle.dot} ${status.mode.is_lab ? '' : 'animate-pulse'}`} />
                            <span className="font-medium capitalize">{status.mode.mode} Mode</span>
                        </div>
                        
                        {status.warnings.length > 0 && (
                            <span className="px-2 py-1 bg-amber-500/20 text-amber-400 rounded-lg text-xs font-medium">
                                {status.warnings.length} warning{status.warnings.length > 1 ? 's' : ''}
                            </span>
                        )}
                    </div>
                    
                    <div className="flex items-center gap-2 text-slate-400">
                        <span className="text-sm">
                            {status.allowlists.length} allowlist{status.allowlists.length !== 1 ? 's' : ''}
                        </span>
                        <span className={`transition-transform ${expanded ? 'rotate-180' : ''}`}>▼</span>
                    </div>
                </div>
                
                <p className="text-sm text-slate-400 mt-2">{status.mode.description}</p>
            </div>

            {/* Expanded content */}
            {expanded && (
                <div className="border-t border-slate-700/50 p-4 space-y-4">
                    {/* Mode flags */}
                    <div className="flex flex-wrap gap-2">
                        {status.mode.dangerous_ok && (
                            <span className="px-2 py-1 bg-red-500/20 text-red-400 rounded text-xs font-medium">
                                🔥 Dangerous OK
                            </span>
                        )}
                        {status.mode.read_only && (
                            <span className="px-2 py-1 bg-blue-500/20 text-blue-400 rounded text-xs font-medium">
                                📖 Read-Only
                            </span>
                        )}
                        {status.mode.prune_enabled && (
                            <span className="px-2 py-1 bg-amber-500/20 text-amber-400 rounded text-xs font-medium">
                                🧹 Prune Enabled
                            </span>
                        )}
                    </div>

                    {/* Warnings */}
                    {status.warnings.length > 0 && (
                        <div className="space-y-2">
                            {status.warnings.map((warning, idx) => (
                                <div key={idx} className="flex items-start gap-2 text-sm bg-amber-500/10 text-amber-400 p-3 rounded-lg border border-amber-500/20">
                                    <span>⚠️</span>
                                    <span>{warning}</span>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Allowlists */}
                    {status.allowlists.length > 0 && (
                        <div className="space-y-3">
                            <h4 className="text-sm font-medium text-slate-300">Active Allowlists</h4>
                            {status.allowlists.map((allowlist) => (
                                <div 
                                    key={allowlist.env_var} 
                                    className={`p-3 rounded-lg border ${
                                        allowlist.is_empty 
                                            ? 'bg-slate-900/50 border-slate-700/50' 
                                            : 'bg-emerald-500/5 border-emerald-500/20'
                                    }`}
                                >
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="font-medium text-slate-200">{allowlist.name}</span>
                                        <span className={`text-xs px-2 py-0.5 rounded ${
                                            allowlist.is_empty 
                                                ? 'bg-slate-700 text-slate-400' 
                                                : 'bg-emerald-500/20 text-emerald-400'
                                        }`}>
                                            {allowlist.count} pattern{allowlist.count !== 1 ? 's' : ''}
                                        </span>
                                    </div>
                                    
                                    <code className="text-xs text-slate-500 block mb-2">{allowlist.env_var}</code>
                                    
                                    {allowlist.entries.length > 0 ? (
                                        <div className="flex flex-wrap gap-1.5 mt-2">
                                            {allowlist.entries.map((entry, idx) => (
                                                <span 
                                                    key={idx}
                                                    className={`px-2 py-0.5 rounded text-xs font-mono ${
                                                        entry.type === 'regex'
                                                            ? 'bg-purple-500/20 text-purple-400'
                                                            : 'bg-slate-700/50 text-slate-300'
                                                    }`}
                                                    title={entry.type === 'regex' ? 'Regex pattern' : 'Exact match'}
                                                >
                                                    {entry.pattern}
                                                </span>
                                            ))}
                                        </div>
                                    ) : (
                                        <span className="text-xs text-slate-500 italic">No patterns configured</span>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Target Check Tool */}
                    <div className="pt-3 border-t border-slate-700/50">
                        <h4 className="text-sm font-medium text-slate-300 mb-3">Check Target Access</h4>
                        <div className="flex gap-2 flex-wrap">
                            <select
                                value={checkTarget.type}
                                onChange={(e) => setCheckTarget({ ...checkTarget, type: e.target.value })}
                                className="bg-slate-900/50 border border-slate-700/50 rounded-lg px-3 py-2 text-sm text-white focus:border-copilot-500 focus:outline-none"
                            >
                                <option value="docker">Docker</option>
                                <option value="proxmox">Proxmox</option>
                            </select>
                            <input
                                type="text"
                                placeholder="Target ID (e.g., container name)"
                                value={checkTarget.id}
                                onChange={(e) => setCheckTarget({ ...checkTarget, id: e.target.value })}
                                onKeyDown={(e) => e.key === 'Enter' && handleCheckTarget()}
                                className="flex-1 min-w-[200px] bg-slate-900/50 border border-slate-700/50 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-copilot-500 focus:outline-none"
                            />
                            <button
                                onClick={handleCheckTarget}
                                disabled={checkLoading || !checkTarget.id.trim()}
                                className="px-4 py-2 bg-copilot-500 hover:bg-copilot-600 disabled:bg-slate-700 disabled:text-slate-400 text-white rounded-lg text-sm font-medium transition-colors"
                            >
                                {checkLoading ? 'Checking...' : 'Check'}
                            </button>
                        </div>

                        {checkResult && (
                            <div className={`mt-3 p-3 rounded-lg border ${
                                checkResult.allowed
                                    ? 'bg-emerald-500/10 border-emerald-500/20'
                                    : 'bg-red-500/10 border-red-500/20'
                            }`}>
                                <div className="flex items-center gap-2 mb-1">
                                    <span className={checkResult.allowed ? 'text-emerald-400' : 'text-red-400'}>
                                        {checkResult.allowed ? '✓ Allowed' : '✗ Blocked'}
                                    </span>
                                </div>
                                <p className="text-sm text-slate-300">{checkResult.reason}</p>
                                
                                {checkResult.matched_pattern && (
                                    <p className="text-xs text-slate-400 mt-1">
                                        Matched: <code className="bg-slate-800 px-1 rounded">{checkResult.matched_pattern}</code>
                                        {checkResult.matched_allowlist && (
                                            <span className="ml-1">from {checkResult.matched_allowlist}</span>
                                        )}
                                    </p>
                                )}
                                
                                {!checkResult.allowed && checkResult.suggestions.length > 0 && (
                                    <div className="mt-2 pt-2 border-t border-slate-700/50">
                                        <span className="text-xs text-slate-400">Suggestions:</span>
                                        <ul className="mt-1 space-y-1">
                                            {checkResult.suggestions.map((suggestion, idx) => (
                                                <li key={idx} className="text-xs text-slate-300 flex items-start gap-1">
                                                    <span className="text-slate-500">•</span>
                                                    {suggestion}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

export default SafetyStatusPanel;
