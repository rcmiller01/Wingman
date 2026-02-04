/**
 * Policy utilities - SINGLE SOURCE OF TRUTH for policy finding display
 * 
 * All ordering, iconography, and formatting for policy findings should
 * come from this file to prevent drift between list/detail/banner views.
 */

import type { PolicyFinding, PolicyFindingLevel, PolicyDecision } from './PolicyFindings';

// --- Severity ordering (single source of truth) ---

export const LEVEL_ORDER: Record<PolicyFindingLevel, number> = {
    block: 0,
    warn: 1,
    info: 2,
};

/**
 * Sort findings by severity: block → warn → info
 * This is THE function to use everywhere for consistent ordering.
 */
export function sortFindingsBySeverity(findings: PolicyFinding[]): PolicyFinding[] {
    return [...findings].sort((a, b) => LEVEL_ORDER[a.level] - LEVEL_ORDER[b.level]);
}

// --- Icons and colors (single source of truth) ---

export const LEVEL_ICONS: Record<PolicyFindingLevel, string> = {
    block: '✕',
    warn: '⚠',
    info: 'ℹ',
};

export const LEVEL_COLORS: Record<PolicyFindingLevel, {
    bg: string;
    border: string;
    text: string;
    iconBg: string;
}> = {
    info: {
        bg: 'bg-blue-500/5',
        border: 'border-blue-500/20',
        text: 'text-blue-400',
        iconBg: 'bg-blue-500/20',
    },
    warn: {
        bg: 'bg-amber-500/5',
        border: 'border-amber-500/20',
        text: 'text-amber-400',
        iconBg: 'bg-amber-500/20',
    },
    block: {
        bg: 'bg-red-500/5',
        border: 'border-red-500/20',
        text: 'text-red-400',
        iconBg: 'bg-red-500/20',
    },
};

// --- Code labels (single source of truth) ---

export const CODE_LABELS: Record<string, string> = {
    'MOCK_MODE_ACTIVE': 'Mock Mode',
    'INTEGRATION_LABEL_MISSING': 'Label Missing',
    'INTEGRATION_LABEL_PRESENT': 'Label Verified',
    'INTEGRATION_PROXMOX_BLOCKED': 'Proxmox Blocked',
    'INTEGRATION_PRUNE_BLOCKED': 'Prune Blocked',
    'INTEGRATION_PRUNE_ALLOWED': 'Prune Allowed',
    'LAB_ALLOWLIST_HIT': 'Allowlist Match',
    'LAB_ALLOWLIST_MISS': 'Not on Allowlist',
    'LAB_DANGEROUS_BLOCKED': 'Dangerous Op Blocked',
    'LAB_DANGEROUS_ALLOWED': 'Dangerous Op Allowed',
    'LAB_READ_ONLY_BLOCKED': 'Read-Only Blocked',
    'SKILL_READ_ONLY': 'Read-Only Skill',
    'POLICY_OK': 'Policy Passed',
    'POLICY_BLOCKED': 'Policy Blocked',
    'ENV_VAR_MISSING': 'Config Missing',
    'SCOPE_LIMITED': 'Scope Limited',
};

export function getCodeLabel(code: string): string {
    return CODE_LABELS[code] || code;
}

// --- Summary generation (for Copy+Share) ---

export interface PolicySummary {
    status: 'allowed' | 'blocked';
    statusIcon: string;
    mode: string;
    findingCounts: {
        block: number;
        warn: number;
        info: number;
    };
    topFindings: string[];
    oneLiner: string;
}

/**
 * Generate a copyable summary of a policy decision.
 * Used for Copy+Share functionality.
 */
export function generatePolicySummary(decision: PolicyDecision, maxFindings = 3): PolicySummary {
    const blockCount = decision.findings.filter(f => f.level === 'block').length;
    const warnCount = decision.findings.filter(f => f.level === 'warn').length;
    const infoCount = decision.findings.filter(f => f.level === 'info').length;
    
    const sorted = sortFindingsBySeverity(decision.findings);
    const topFindings = sorted.slice(0, maxFindings).map(f => 
        `${LEVEL_ICONS[f.level]} [${f.code}] ${f.message}`
    );
    
    const status = decision.allowed ? 'allowed' : 'blocked';
    const statusIcon = decision.allowed ? '✓' : '✕';
    
    // Build one-liner
    const parts = [`${statusIcon} ${status.toUpperCase()}`];
    if (blockCount > 0) parts.push(`${blockCount} blocked`);
    if (warnCount > 0) parts.push(`${warnCount} warnings`);
    parts.push(`mode=${decision.mode}`);
    
    return {
        status,
        statusIcon,
        mode: decision.mode,
        findingCounts: { block: blockCount, warn: warnCount, info: infoCount },
        topFindings,
        oneLiner: parts.join(' | '),
    };
}

/**
 * Format a policy decision for clipboard copying.
 */
export function formatPolicyForClipboard(decision: PolicyDecision): string {
    const summary = generatePolicySummary(decision);
    const lines = [
        `Policy Decision: ${summary.statusIcon} ${summary.status.toUpperCase()}`,
        `Mode: ${decision.mode}`,
        `Checked: ${new Date(decision.checked_at).toLocaleString()}`,
        '',
        'Findings:',
        ...summary.topFindings,
    ];
    
    if (decision.findings.length > 3) {
        lines.push(`... and ${decision.findings.length - 3} more`);
    }
    
    return lines.join('\n');
}

// --- Clipboard utilities ---

export async function copyToClipboard(text: string): Promise<boolean> {
    try {
        await navigator.clipboard.writeText(text);
        return true;
    } catch {
        // Fallback for older browsers
        try {
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
            return true;
        } catch {
            return false;
        }
    }
}

// --- Hash generation for policy decision caching ---

/**
 * Generate a simple hash of a policy decision for caching.
 * Used to detect if policy decision has changed between preview and create.
 */
export function hashPolicyDecision(decision: PolicyDecision): string {
    const content = JSON.stringify({
        allowed: decision.allowed,
        mode: decision.mode,
        findings: decision.findings.map(f => f.code).sort(),
    });
    
    // Simple string hash (djb2 algorithm)
    let hash = 5381;
    for (let i = 0; i < content.length; i++) {
        hash = ((hash << 5) + hash) + content.charCodeAt(i);
    }
    return (hash >>> 0).toString(16);
}
