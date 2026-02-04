'use client';

interface SafetyCheckBadgeProps {
    mode: 'mock' | 'integration' | 'lab';
    riskLevel: 'low' | 'medium' | 'high';
    warnings?: string[];
    className?: string;
}

export function SafetyCheckBadge({ mode, riskLevel, warnings = [], className = '' }: SafetyCheckBadgeProps) {
    const hasWarnings = warnings.length > 0;
    
    // Color based on risk and warnings
    const getBadgeColor = () => {
        if (mode === 'mock') {
            return 'bg-purple-500/20 text-purple-400 border-purple-500/30';
        }
        if (hasWarnings) {
            return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
        }
        if (riskLevel === 'high') {
            return 'bg-red-500/20 text-red-400 border-red-500/30';
        }
        if (riskLevel === 'medium') {
            return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
        }
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
    };

    const getIcon = () => {
        if (hasWarnings) return '⚠';
        if (riskLevel === 'high' || mode === 'lab') return '🛡️';
        return '✓';
    };

    const getLabel = () => {
        if (mode === 'mock') return 'Mock';
        if (mode === 'lab') return 'Lab';
        return 'Integration';
    };

    return (
        <div className={className}>
            <div className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium border ${getBadgeColor()}`}>
                <span>{getIcon()}</span>
                <span>{getLabel()}</span>
            </div>
            
            {hasWarnings && (
                <div className="mt-2 space-y-1">
                    {warnings.map((warning, index) => (
                        <div 
                            key={index}
                            className="flex items-start gap-2 text-xs bg-amber-500/10 border border-amber-500/20 rounded-lg px-2 py-1.5"
                        >
                            <span className="text-amber-400 mt-0.5 flex-shrink-0">⚠</span>
                            <span className="text-amber-200">{warning}</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

interface SafetyPolicyInfoProps {
    mode: 'mock' | 'integration' | 'lab';
}

export function SafetyPolicyInfo({ mode }: SafetyPolicyInfoProps) {
    const policyInfo = {
        mock: {
            title: 'Mock Mode',
            description: 'All operations return canned responses. No real infrastructure changes.',
            constraints: [
                'All skills allowed',
                'All targets allowed',
                'No actual execution',
            ],
            color: 'purple',
        },
        integration: {
            title: 'Integration Mode',
            description: 'Real Docker operations, mocked Proxmox.',
            constraints: [
                'Docker containers with wingman.test=true label only',
                'Read-only diagnostic skills freely allowed',
                'Prune operations blocked by default',
            ],
            color: 'blue',
        },
        lab: {
            title: 'Lab Mode',
            description: 'Real infrastructure operations with strict allowlists.',
            constraints: [
                'Targets must be in explicit allowlist',
                'Dangerous operations require LAB_DANGEROUS_OK=true',
                'Read-only skills always allowed',
            ],
            color: 'emerald',
        },
    };

    const info = policyInfo[mode];
    const colorMap = {
        purple: 'border-purple-500/30 bg-purple-500/5',
        blue: 'border-blue-500/30 bg-blue-500/5',
        emerald: 'border-emerald-500/30 bg-emerald-500/5',
    };

    return (
        <div className={`rounded-xl border p-4 ${colorMap[info.color as keyof typeof colorMap]}`}>
            <h4 className="font-medium text-white mb-1">{info.title}</h4>
            <p className="text-sm text-slate-400 mb-3">{info.description}</p>
            <div className="space-y-1">
                {info.constraints.map((constraint, index) => (
                    <div key={index} className="flex items-center gap-2 text-xs text-slate-300">
                        <span className="w-1 h-1 rounded-full bg-slate-500" />
                        {constraint}
                    </div>
                ))}
            </div>
        </div>
    );
}

export default SafetyCheckBadge;
