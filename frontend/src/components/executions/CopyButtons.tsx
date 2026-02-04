'use client';

import { useState, useCallback } from 'react';
import { copyToClipboard, formatPolicyForClipboard, generatePolicySummary } from './policyUtils';
import type { PolicyDecision } from './PolicyFindings';

interface CopyButtonProps {
    text: string;
    label?: string;
    className?: string;
}

/**
 * Simple copy-to-clipboard button with success feedback.
 */
export function CopyButton({ text, label = 'Copy', className = '' }: CopyButtonProps) {
    const [copied, setCopied] = useState(false);

    const handleCopy = useCallback(async () => {
        const success = await copyToClipboard(text);
        if (success) {
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    }, [text]);

    return (
        <button
            onClick={handleCopy}
            className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                copied
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : 'bg-slate-700/50 text-slate-400 hover:text-white hover:bg-slate-700'
            } ${className}`}
            title={copied ? 'Copied!' : label}
        >
            <span>{copied ? '✓' : '📋'}</span>
            <span>{copied ? 'Copied!' : label}</span>
        </button>
    );
}

interface CopyIdButtonProps {
    id: string;
    className?: string;
}

/**
 * Copy execution ID button.
 */
export function CopyIdButton({ id, className = '' }: CopyIdButtonProps) {
    return (
        <CopyButton 
            text={id} 
            label="Copy ID" 
            className={className}
        />
    );
}

interface CopyPolicySummaryButtonProps {
    decision: PolicyDecision;
    className?: string;
}

/**
 * Copy policy summary (allowed/blocked + top findings).
 */
export function CopyPolicySummaryButton({ decision, className = '' }: CopyPolicySummaryButtonProps) {
    const summary = formatPolicyForClipboard(decision);
    
    return (
        <CopyButton 
            text={summary} 
            label="Copy Policy Summary" 
            className={className}
        />
    );
}

interface CopyJsonButtonProps {
    data: unknown;
    label?: string;
    className?: string;
}

/**
 * Copy full JSON export.
 */
export function CopyJsonButton({ data, label = 'Copy JSON', className = '' }: CopyJsonButtonProps) {
    const json = JSON.stringify(data, null, 2);
    
    return (
        <CopyButton 
            text={json} 
            label={label} 
            className={className}
        />
    );
}

interface ShareToolbarProps {
    executionId: string;
    policyDecision?: PolicyDecision | null;
    fullData?: unknown;
    className?: string;
}

/**
 * Toolbar with Copy ID, Copy Policy Summary, Copy JSON buttons.
 * The "boring" but essential UX affordance.
 */
export function ShareToolbar({ executionId, policyDecision, fullData, className = '' }: ShareToolbarProps) {
    return (
        <div className={`flex items-center gap-2 flex-wrap ${className}`}>
            <CopyIdButton id={executionId} />
            {policyDecision && (
                <CopyPolicySummaryButton decision={policyDecision} />
            )}
            {fullData !== undefined && fullData !== null && (
                <CopyJsonButton data={fullData} />
            )}
        </div>
    );
}

export default CopyButton;
