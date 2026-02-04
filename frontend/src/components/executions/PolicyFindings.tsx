'use client';

import { useState } from 'react';
import { 
    LEVEL_COLORS, 
    LEVEL_ICONS, 
    CODE_LABELS,
    sortFindingsBySeverity,
    getCodeLabel,
} from './policyUtils';

// Types matching backend PolicyFinding schema
export type PolicyFindingLevel = 'info' | 'warn' | 'block';

export interface PolicyFinding {
    level: PolicyFindingLevel;
    code: string;
    message: string;
    details?: Record<string, unknown>;
    rule?: string;
    timestamp?: string;
}

export interface PolicyDecision {
    allowed: boolean;
    findings: PolicyFinding[];
    mode: 'mock' | 'integration' | 'lab';
    checked_at: string;
}

// Re-export from policyUtils for convenience (but policyUtils is source of truth)
export { LEVEL_COLORS as levelColors, LEVEL_ICONS as levelIcons, CODE_LABELS as codeLabels };

interface PolicyFindingCardProps {
    finding: PolicyFinding;
    showDetails?: boolean;
}

export function PolicyFindingCard({ finding, showDetails = false }: PolicyFindingCardProps) {
    const [expanded, setExpanded] = useState(showDetails);
    const colors = LEVEL_COLORS[finding.level];
    const icon = LEVEL_ICONS[finding.level];
    const hasExpandableContent = finding.details || finding.rule;

    return (
        <div
            className={`rounded-lg border ${colors.bg} ${colors.border} overflow-hidden transition-all`}
        >
            <button
                onClick={() => hasExpandableContent && setExpanded(!expanded)}
                className={`w-full flex items-start gap-3 px-3 py-2.5 text-left ${
                    hasExpandableContent ? 'cursor-pointer hover:bg-white/5' : 'cursor-default'
                }`}
            >
                {/* Level icon */}
                <div className={`w-6 h-6 rounded-full ${colors.iconBg} flex items-center justify-center flex-shrink-0`}>
                    <span className={`text-xs ${colors.text}`}>{icon}</span>
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                        <span className={`text-sm font-medium ${colors.text}`}>
                            {getCodeLabel(finding.code)}
                        </span>
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-800/50 text-slate-500">
                            {finding.code}
                        </span>
                    </div>
                    <p className="text-sm text-slate-300 mt-0.5">{finding.message}</p>
                </div>

                {/* Expand indicator */}
                {hasExpandableContent && (
                    <span className={`text-slate-500 transition-transform ${expanded ? 'rotate-180' : ''}`}>
                        ▼
                    </span>
                )}
            </button>

            {/* Expanded content */}
            {expanded && hasExpandableContent && (
                <div className="px-3 pb-3 pl-12 space-y-2">
                    {finding.rule && (
                        <div className="text-xs">
                            <span className="text-slate-500">Rule: </span>
                            <code className="text-slate-300 bg-slate-800/50 px-1.5 py-0.5 rounded">
                                {finding.rule}
                            </code>
                        </div>
                    )}
                    {finding.details && Object.keys(finding.details).length > 0 && (
                        <div className="bg-slate-900/50 rounded-lg p-2 text-xs font-mono">
                            {Object.entries(finding.details).map(([key, value]) => (
                                <div key={key} className="flex gap-2">
                                    <span className="text-slate-500">{key}:</span>
                                    <span className="text-slate-300">{JSON.stringify(value)}</span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

interface PolicyFindingsListProps {
    findings: PolicyFinding[];
    maxVisible?: number;
    title?: string;
}

export function PolicyFindingsList({ findings, maxVisible, title }: PolicyFindingsListProps) {
    const [showAll, setShowAll] = useState(false);

    if (findings.length === 0) {
        return (
            <div className="text-sm text-slate-500 italic">No policy findings</div>
        );
    }

    // Use centralized sorting (single source of truth for severity order)
    const sortedFindings = sortFindingsBySeverity(findings);

    const visibleFindings = maxVisible && !showAll 
        ? sortedFindings.slice(0, maxVisible)
        : sortedFindings;
    const hiddenCount = sortedFindings.length - visibleFindings.length;

    return (
        <div className="space-y-2">
            {title && (
                <h4 className="text-sm font-medium text-slate-400">{title}</h4>
            )}
            {visibleFindings.map((finding, index) => (
                <PolicyFindingCard key={index} finding={finding} />
            ))}
            {hiddenCount > 0 && (
                <button
                    onClick={() => setShowAll(true)}
                    className="text-sm text-copilot-400 hover:text-copilot-300"
                >
                    Show {hiddenCount} more finding{hiddenCount !== 1 ? 's' : ''}...
                </button>
            )}
            {showAll && maxVisible && sortedFindings.length > maxVisible && (
                <button
                    onClick={() => setShowAll(false)}
                    className="text-sm text-copilot-400 hover:text-copilot-300"
                >
                    Show less
                </button>
            )}
        </div>
    );
}

interface PolicyDecisionBannerProps {
    decision: PolicyDecision;
    compact?: boolean;
}

export function PolicyDecisionBanner({ decision, compact = false }: PolicyDecisionBannerProps) {
    const blockCount = decision.findings.filter(f => f.level === 'block').length;
    const warnCount = decision.findings.filter(f => f.level === 'warn').length;
    const infoCount = decision.findings.filter(f => f.level === 'info').length;

    const colors = decision.allowed
        ? {
            bg: 'bg-emerald-500/10',
            border: 'border-emerald-500/30',
            text: 'text-emerald-400',
            icon: '✓',
        }
        : {
            bg: 'bg-red-500/10',
            border: 'border-red-500/30',
            text: 'text-red-400',
            icon: '✕',
        };

    if (compact) {
        return (
            <div className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-lg border ${colors.bg} ${colors.border}`}>
                <span className={colors.text}>{colors.icon}</span>
                <span className={`text-sm font-medium ${colors.text}`}>
                    {decision.allowed ? 'Allowed' : 'Blocked'}
                </span>
                {(blockCount > 0 || warnCount > 0) && (
                    <div className="flex items-center gap-1.5 text-xs">
                        {blockCount > 0 && (
                            <span className="text-red-400">{blockCount} block</span>
                        )}
                        {warnCount > 0 && (
                            <span className="text-amber-400">{warnCount} warn</span>
                        )}
                    </div>
                )}
            </div>
        );
    }

    return (
        <div className={`rounded-xl border p-4 ${colors.bg} ${colors.border}`}>
            <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center ${colors.bg} border ${colors.border}`}>
                        <span className={`text-xl ${colors.text}`}>{colors.icon}</span>
                    </div>
                    <div>
                        <h4 className={`font-semibold ${colors.text}`}>
                            {decision.allowed ? 'Execution Allowed' : 'Execution Blocked'}
                        </h4>
                        <p className="text-xs text-slate-400">
                            Mode: {decision.mode} • Checked: {new Date(decision.checked_at).toLocaleString()}
                        </p>
                    </div>
                </div>
                
                {/* Summary badges */}
                <div className="flex items-center gap-2">
                    {blockCount > 0 && (
                        <span className="px-2 py-1 rounded bg-red-500/20 text-red-400 text-xs font-medium">
                            {blockCount} blocked
                        </span>
                    )}
                    {warnCount > 0 && (
                        <span className="px-2 py-1 rounded bg-amber-500/20 text-amber-400 text-xs font-medium">
                            {warnCount} warnings
                        </span>
                    )}
                    {infoCount > 0 && (
                        <span className="px-2 py-1 rounded bg-blue-500/20 text-blue-400 text-xs font-medium">
                            {infoCount} info
                        </span>
                    )}
                </div>
            </div>

            {decision.findings.length > 0 && (
                <PolicyFindingsList findings={decision.findings} maxVisible={3} />
            )}
        </div>
    );
}

// Summary component for quick glance at policy decision
interface PolicyDecisionSummaryProps {
    decision: PolicyDecision | null;
}

export function PolicyDecisionSummary({ decision }: PolicyDecisionSummaryProps) {
    if (!decision) {
        return (
            <span className="text-xs text-slate-500 italic">No policy check</span>
        );
    }

    const blockCount = decision.findings.filter(f => f.level === 'block').length;
    const warnCount = decision.findings.filter(f => f.level === 'warn').length;

    if (!decision.allowed) {
        return (
            <span className="flex items-center gap-1.5 text-xs text-red-400">
                <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
                Blocked ({blockCount})
            </span>
        );
    }

    if (warnCount > 0) {
        return (
            <span className="flex items-center gap-1.5 text-xs text-amber-400">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                {warnCount} warning{warnCount !== 1 ? 's' : ''}
            </span>
        );
    }

    return (
        <span className="flex items-center gap-1.5 text-xs text-emerald-400">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            Passed
        </span>
    );
}

export default PolicyFindingCard;
