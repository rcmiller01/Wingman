'use client';

import { useState } from 'react';
import { PolicyDecision, PolicyFindingsList, PolicyDecisionBanner } from './PolicyFindings';

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

interface PreviewModalProps {
    skill: Skill;
    parameters: Record<string, string>;
    preview: PreviewResponse | null;
    loading: boolean;
    onClose: () => void;
    onConfirm: () => void;
    onBack: () => void;
}

const riskColors: Record<string, { bg: string; text: string; border: string }> = {
    low: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/30' },
    medium: { bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/30' },
    high: { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/30' },
};

const modeColors: Record<string, { bg: string; text: string; border: string; icon: string }> = {
    mock: { bg: 'bg-purple-500/10', text: 'text-purple-400', border: 'border-purple-500/30', icon: '🧪' },
    integration: { bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/30', icon: '🔧' },
    lab: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/30', icon: '🏠' },
};

export function PreviewModal({ skill, parameters, preview, loading, onClose, onConfirm, onBack }: PreviewModalProps) {
    const [acknowledged, setAcknowledged] = useState(false);

    const canProceed = preview && preview.policy_decision.allowed && (
        preview.risk_level === 'low' || acknowledged
    );

    const hasWarnings = preview?.policy_decision.findings.some(f => f.level === 'warn');
    const hasBlocks = preview?.policy_decision.findings.some(f => f.level === 'block');

    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
            <div className="bg-slate-800 rounded-2xl border border-slate-700 w-full max-w-2xl max-h-[85vh] overflow-hidden flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-slate-700">
                    <div>
                        <h2 className="text-xl font-bold text-white">Preview Execution</h2>
                        <p className="text-sm text-slate-400">Review before creating execution request</p>
                    </div>
                    <button onClick={onClose} className="text-slate-400 hover:text-white text-xl">
                        ✕
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-auto p-6 space-y-6">
                    {loading ? (
                        <div className="flex flex-col items-center justify-center py-12">
                            <div className="w-10 h-10 border-2 border-copilot-500 border-t-transparent rounded-full animate-spin mb-4" />
                            <p className="text-slate-400">Checking policy constraints...</p>
                        </div>
                    ) : preview ? (
                        <>
                            {/* Skill summary */}
                            <div className="bg-slate-700/30 rounded-xl p-4">
                                <div className="flex items-start justify-between mb-3">
                                    <div>
                                        <h3 className="font-semibold text-white">{skill.name}</h3>
                                        <p className="text-sm text-slate-400 mt-1">{skill.description}</p>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        {/* Mode badge */}
                                        <span className={`px-2.5 py-1 rounded-lg text-xs font-medium ${modeColors[preview.mode]?.bg} ${modeColors[preview.mode]?.text} border ${modeColors[preview.mode]?.border}`}>
                                            {modeColors[preview.mode]?.icon} {preview.mode}
                                        </span>
                                        {/* Risk badge */}
                                        <span className={`px-2.5 py-1 rounded-lg text-xs font-medium ${riskColors[preview.risk_level]?.bg} ${riskColors[preview.risk_level]?.text} border ${riskColors[preview.risk_level]?.border}`}>
                                            {preview.risk_level} risk
                                        </span>
                                    </div>
                                </div>

                                {/* Duration estimate */}
                                <div className="text-xs text-slate-500">
                                    <span>Estimated duration: </span>
                                    <span className="text-slate-300">{preview.estimated_duration_seconds}s</span>
                                </div>
                            </div>

                            {/* Parameters */}
                            {Object.keys(parameters).length > 0 && (
                                <div>
                                    <h4 className="text-sm font-medium text-slate-400 mb-2">Parameters</h4>
                                    <div className="bg-slate-900/50 rounded-lg p-3 font-mono text-sm space-y-1">
                                        {Object.entries(parameters).map(([key, value]) => (
                                            <div key={key} className="flex">
                                                <span className="text-slate-500 w-32 flex-shrink-0">{key}:</span>
                                                <span className="text-slate-300">{value || '(empty)'}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Targets affected */}
                            {preview.targets_affected.length > 0 && (
                                <div>
                                    <h4 className="text-sm font-medium text-slate-400 mb-2">Targets Affected</h4>
                                    <div className="flex flex-wrap gap-2">
                                        {preview.targets_affected.map((target, idx) => (
                                            <span 
                                                key={idx}
                                                className="px-2.5 py-1 bg-slate-700/50 rounded-lg text-sm text-slate-300 font-mono"
                                            >
                                                {target}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Policy Decision */}
                            <div>
                                <h4 className="text-sm font-medium text-slate-400 mb-2">Policy Check</h4>
                                <PolicyDecisionBanner decision={preview.policy_decision} />
                            </div>

                            {/* Warning acknowledgment */}
                            {preview.policy_decision.allowed && (preview.risk_level === 'high' || preview.risk_level === 'medium' || hasWarnings) && (
                                <label className="flex items-start gap-3 p-4 bg-amber-500/5 rounded-xl border border-amber-500/20 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={acknowledged}
                                        onChange={(e) => setAcknowledged(e.target.checked)}
                                        className="mt-1 w-4 h-4 rounded border-amber-500/50 bg-slate-800 checked:bg-amber-500"
                                    />
                                    <div>
                                        <span className="text-amber-400 font-medium">
                                            I understand the risks
                                        </span>
                                        <p className="text-sm text-slate-400 mt-1">
                                            This execution is {preview.risk_level} risk
                                            {hasWarnings && ' and has policy warnings'}.
                                            I confirm I want to proceed.
                                        </p>
                                    </div>
                                </label>
                            )}
                        </>
                    ) : (
                        <div className="text-center py-12 text-red-400">
                            Failed to load preview. Please try again.
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between p-6 border-t border-slate-700 bg-slate-800/50">
                    <button
                        onClick={onBack}
                        className="px-4 py-2 text-slate-400 hover:text-white transition-colors"
                    >
                        ← Back to Edit
                    </button>

                    <div className="flex items-center gap-3">
                        <button
                            onClick={onClose}
                            className="px-4 py-2 text-slate-400 hover:text-white transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={onConfirm}
                            disabled={!canProceed}
                            className={`px-6 py-2 rounded-lg font-medium transition-colors ${
                                canProceed
                                    ? 'bg-copilot-500 hover:bg-copilot-600 text-white'
                                    : 'bg-slate-700 text-slate-500 cursor-not-allowed'
                            }`}
                        >
                            {hasBlocks ? 'Cannot Create (Blocked)' : 'Create Execution Request'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

// Simple skill selection step
interface SkillSelectionStepProps {
    skills: Skill[];
    selectedSkill: Skill | null;
    onSelectSkill: (skill: Skill) => void;
    onClose: () => void;
}

export function SkillSelectionStep({ skills, selectedSkill, onSelectSkill, onClose }: SkillSelectionStepProps) {
    const [searchTerm, setSearchTerm] = useState('');
    const [categoryFilter, setCategoryFilter] = useState('all');

    const categories = ['all', ...Array.from(new Set(skills.map(s => s.category)))];
    
    const filteredSkills = skills.filter(skill => {
        const matchesSearch = 
            skill.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            skill.description.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesCategory = categoryFilter === 'all' || skill.category === categoryFilter;
        return matchesSearch && matchesCategory;
    });

    // Group skills by category
    const groupedSkills = filteredSkills.reduce((acc, skill) => {
        if (!acc[skill.category]) acc[skill.category] = [];
        acc[skill.category].push(skill);
        return acc;
    }, {} as Record<string, Skill[]>);

    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
            <div className="bg-slate-800 rounded-2xl border border-slate-700 w-full max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-slate-700">
                    <div>
                        <h2 className="text-xl font-bold text-white">Select Skill</h2>
                        <p className="text-sm text-slate-400">Choose a skill to execute</p>
                    </div>
                    <button onClick={onClose} className="text-slate-400 hover:text-white text-xl">
                        ✕
                    </button>
                </div>

                {/* Search and filter */}
                <div className="p-4 border-b border-slate-700/50 space-y-3">
                    <input
                        type="text"
                        placeholder="Search skills..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-4 py-2 text-white placeholder-slate-500 focus:border-copilot-500 focus:outline-none"
                    />
                    <div className="flex gap-2 flex-wrap">
                        {categories.map((cat) => (
                            <button
                                key={cat}
                                onClick={() => setCategoryFilter(cat)}
                                className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                                    categoryFilter === cat
                                        ? 'bg-copilot-500/20 text-copilot-400 border border-copilot-500/30'
                                        : 'bg-slate-700/50 text-slate-400 border border-transparent hover:border-slate-600'
                                }`}
                            >
                                {cat === 'all' ? 'All' : cat}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Skills list */}
                <div className="flex-1 overflow-auto p-4 space-y-4">
                    {Object.entries(groupedSkills).map(([category, categorySkills]) => (
                        <div key={category}>
                            <h3 className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">
                                {category}
                            </h3>
                            <div className="space-y-2">
                                {categorySkills.map((skill) => (
                                    <button
                                        key={skill.id}
                                        onClick={() => onSelectSkill(skill)}
                                        className={`w-full text-left rounded-xl p-4 transition-colors border ${
                                            selectedSkill?.id === skill.id
                                                ? 'bg-copilot-500/10 border-copilot-500/30'
                                                : 'bg-slate-700/30 border-transparent hover:bg-slate-700/50 hover:border-slate-600'
                                        }`}
                                    >
                                        <div className="flex items-start justify-between">
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2 mb-1">
                                                    <span className="font-medium text-white">{skill.name}</span>
                                                    {skill.requires_confirmation && (
                                                        <span className="text-xs text-amber-400">⚠ requires approval</span>
                                                    )}
                                                </div>
                                                <p className="text-sm text-slate-400 line-clamp-2">{skill.description}</p>
                                            </div>
                                            <span className={`ml-3 px-2 py-0.5 rounded text-xs font-medium flex-shrink-0 ${
                                                riskColors[skill.risk]?.bg || 'bg-slate-600'
                                            } ${riskColors[skill.risk]?.text || 'text-slate-300'}`}>
                                                {skill.risk}
                                            </span>
                                        </div>
                                    </button>
                                ))}
                            </div>
                        </div>
                    ))}

                    {filteredSkills.length === 0 && (
                        <div className="text-center py-8 text-slate-500">
                            No skills found matching your search.
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

// Parameter entry step
interface ParameterEntryStepProps {
    skill: Skill;
    parameters: Record<string, string>;
    onChange: (params: Record<string, string>) => void;
    onBack: () => void;
    onPreview: () => void;
    onClose: () => void;
}

export function ParameterEntryStep({ skill, parameters, onChange, onBack, onPreview, onClose }: ParameterEntryStepProps) {
    const updateParam = (key: string, value: string) => {
        onChange({ ...parameters, [key]: value });
    };

    const requiredFilled = skill.required_params.every(p => parameters[p]?.trim());

    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
            <div className="bg-slate-800 rounded-2xl border border-slate-700 w-full max-w-xl max-h-[80vh] overflow-hidden flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-slate-700">
                    <div>
                        <h2 className="text-xl font-bold text-white">Configure Parameters</h2>
                        <p className="text-sm text-slate-400">{skill.name}</p>
                    </div>
                    <button onClick={onClose} className="text-slate-400 hover:text-white text-xl">
                        ✕
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-auto p-6 space-y-6">
                    {/* Skill info */}
                    <div className="bg-slate-700/30 rounded-xl p-4">
                        <p className="text-sm text-slate-400">{skill.description}</p>
                        <div className="flex items-center gap-4 mt-3 text-xs text-slate-500">
                            <span>Category: {skill.category}</span>
                            <span>Risk: <span className={riskColors[skill.risk]?.text}>{skill.risk}</span></span>
                            <span>Est: {skill.estimated_duration_seconds}s</span>
                        </div>
                    </div>

                    {/* Required parameters */}
                    {skill.required_params.length > 0 && (
                        <div className="space-y-4">
                            <h3 className="text-sm font-medium text-slate-300 flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-red-400" />
                                Required Parameters
                            </h3>
                            {skill.required_params.map((param) => (
                                <div key={param}>
                                    <label className="block text-sm text-slate-400 mb-1.5">{param}</label>
                                    <input
                                        type="text"
                                        value={parameters[param] || ''}
                                        onChange={(e) => updateParam(param, e.target.value)}
                                        placeholder={`Enter ${param}`}
                                        className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:border-copilot-500 focus:outline-none"
                                    />
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Optional parameters */}
                    {skill.optional_params.length > 0 && (
                        <div className="space-y-4">
                            <h3 className="text-sm font-medium text-slate-500">Optional Parameters</h3>
                            {skill.optional_params.map((param) => (
                                <div key={param}>
                                    <label className="block text-sm text-slate-400 mb-1.5">{param}</label>
                                    <input
                                        type="text"
                                        value={parameters[param] || ''}
                                        onChange={(e) => updateParam(param, e.target.value)}
                                        placeholder={`Enter ${param} (optional)`}
                                        className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:border-copilot-500 focus:outline-none"
                                    />
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between p-6 border-t border-slate-700">
                    <button
                        onClick={onBack}
                        className="px-4 py-2 text-slate-400 hover:text-white transition-colors"
                    >
                        ← Change Skill
                    </button>
                    <button
                        onClick={onPreview}
                        disabled={!requiredFilled}
                        className={`px-6 py-2 rounded-lg font-medium transition-colors ${
                            requiredFilled
                                ? 'bg-copilot-500 hover:bg-copilot-600 text-white'
                                : 'bg-slate-700 text-slate-500 cursor-not-allowed'
                        }`}
                    >
                        Preview Execution →
                    </button>
                </div>
            </div>
        </div>
    );
}

export default PreviewModal;
