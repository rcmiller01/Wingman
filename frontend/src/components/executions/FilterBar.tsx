'use client';

import { useState, useEffect, useRef, useCallback } from 'react';

export interface FilterState {
    status: string;
    risk: string;
    mode: string;
    skill_id: string;
    target: string;
    search: string;
    sort: 'newest' | 'oldest_pending';
    needs_attention: boolean;
}

const defaultFilters: FilterState = {
    status: 'all',
    risk: 'all',
    mode: 'all',
    skill_id: '',
    target: '',
    search: '',
    sort: 'newest',
    needs_attention: true,  // Default to "what needs me right now?" view
};

// Alternative default for "show everything" view
const showAllFilters: FilterState = {
    status: 'all',
    risk: 'all',
    mode: 'all',
    skill_id: '',
    target: '',
    search: '',
    sort: 'newest',
    needs_attention: false,
};

// Debounce delay for search input (ms)
const SEARCH_DEBOUNCE_MS = 200;

/**
 * Hook for debouncing a value.
 */
function useDebounce<T>(value: T, delay: number): T {
    const [debouncedValue, setDebouncedValue] = useState(value);

    useEffect(() => {
        const handler = setTimeout(() => {
            setDebouncedValue(value);
        }, delay);

        return () => {
            clearTimeout(handler);
        };
    }, [value, delay]);

    return debouncedValue;
}

interface FilterBarProps {
    filters: FilterState;
    onChange: (filters: FilterState) => void;
    skills?: Array<{ id: string; name: string }>;
    showAdvanced?: boolean;
}

const statusOptions = [
    { value: 'all', label: 'All Status' },
    { value: 'pending_approval', label: 'Pending' },
    { value: 'approved', label: 'Approved' },
    { value: 'rejected', label: 'Rejected' },
    { value: 'completed', label: 'Completed' },
    { value: 'failed', label: 'Failed' },
];

const riskOptions = [
    { value: 'all', label: 'All Risk' },
    { value: 'low', label: 'Low' },
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' },
];

const modeOptions = [
    { value: 'all', label: 'All Modes' },
    { value: 'mock', label: 'Mock' },
    { value: 'integration', label: 'Integration' },
    { value: 'lab', label: 'Lab' },
];

const sortOptions = [
    { value: 'newest', label: 'Newest First' },
    { value: 'oldest_pending', label: 'Oldest Pending' },
];

export function FilterBar({ filters, onChange, skills = [], showAdvanced = true }: FilterBarProps) {
    const [expanded, setExpanded] = useState(false);
    
    // Local search state for immediate UI feedback
    const [localSearch, setLocalSearch] = useState(filters.search);
    
    // Debounce search to avoid hammering the API
    const debouncedSearch = useDebounce(localSearch, SEARCH_DEBOUNCE_MS);
    
    // Sync debounced search back to parent
    useEffect(() => {
        if (debouncedSearch !== filters.search) {
            onChange({ ...filters, search: debouncedSearch });
        }
    }, [debouncedSearch]); // Intentionally omit filters/onChange to avoid loops
    
    // Sync external filter changes to local state
    useEffect(() => {
        setLocalSearch(filters.search);
    }, [filters.search]);

    const updateFilter = <K extends keyof FilterState>(key: K, value: FilterState[K]) => {
        onChange({ ...filters, [key]: value });
    };

    const clearFilters = () => {
        onChange(showAllFilters);  // Clear to show everything
    };

    const hasActiveFilters = 
        filters.status !== 'all' ||
        filters.risk !== 'all' ||
        filters.mode !== 'all' ||
        filters.skill_id !== '' ||
        filters.target !== '' ||
        filters.search !== '' ||
        filters.needs_attention;

    return (
        <div className="space-y-3">
            {/* Main filter row */}
            <div className="flex items-center gap-3 flex-wrap">
                {/* Quick filters - Status chips */}
                <div className="flex items-center gap-1.5">
                    {statusOptions.slice(0, 3).map((opt) => (
                        <button
                            key={opt.value}
                            onClick={() => updateFilter('status', opt.value)}
                            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                                filters.status === opt.value
                                    ? 'bg-copilot-500/20 text-copilot-400 border border-copilot-500/30'
                                    : 'bg-slate-800/50 text-slate-400 border border-slate-700/50 hover:border-slate-600'
                            }`}
                        >
                            {opt.label}
                        </button>
                    ))}
                </div>

                {/* Needs attention toggle */}
                <button
                    onClick={() => updateFilter('needs_attention', !filters.needs_attention)}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                        filters.needs_attention
                            ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                            : 'bg-slate-800/50 text-slate-400 border border-slate-700/50 hover:border-slate-600'
                    }`}
                >
                    <span className={`w-2 h-2 rounded-full ${filters.needs_attention ? 'bg-amber-400 animate-pulse' : 'bg-slate-500'}`} />
                    Needs Attention
                </button>

                {/* Search box */}
                <div className="relative flex-1 min-w-[200px] max-w-md">
                    <input
                        type="text"
                        placeholder="Search by ID, container, skill..."
                        value={localSearch}
                        onChange={(e) => setLocalSearch(e.target.value)}
                        className="w-full bg-slate-800/50 border border-slate-700/50 rounded-lg pl-9 pr-3 py-1.5 text-sm text-white placeholder-slate-500 focus:border-copilot-500 focus:outline-none"
                    />
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 text-sm">🔍</span>
                </div>

                {/* Expand/collapse */}
                {showAdvanced && (
                    <button
                        onClick={() => setExpanded(!expanded)}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-slate-400 hover:text-white transition-colors"
                    >
                        <span className={`transition-transform ${expanded ? 'rotate-180' : ''}`}>▼</span>
                        {expanded ? 'Less filters' : 'More filters'}
                    </button>
                )}

                {/* Clear filters */}
                {hasActiveFilters && (
                    <button
                        onClick={clearFilters}
                        className="px-3 py-1.5 text-sm text-slate-400 hover:text-red-400 transition-colors"
                    >
                        ✕ Clear
                    </button>
                )}
            </div>

            {/* Expanded filters */}
            {expanded && (
                <div className="flex items-center gap-3 flex-wrap p-3 bg-slate-800/30 rounded-xl border border-slate-700/30">
                    {/* Status dropdown (full list) */}
                    <div className="flex flex-col gap-1">
                        <label className="text-xs text-slate-500">Status</label>
                        <select
                            value={filters.status}
                            onChange={(e) => updateFilter('status', e.target.value)}
                            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:border-copilot-500 focus:outline-none"
                        >
                            {statusOptions.map((opt) => (
                                <option key={opt.value} value={opt.value}>{opt.label}</option>
                            ))}
                        </select>
                    </div>

                    {/* Risk dropdown */}
                    <div className="flex flex-col gap-1">
                        <label className="text-xs text-slate-500">Risk Level</label>
                        <select
                            value={filters.risk}
                            onChange={(e) => updateFilter('risk', e.target.value)}
                            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:border-copilot-500 focus:outline-none"
                        >
                            {riskOptions.map((opt) => (
                                <option key={opt.value} value={opt.value}>{opt.label}</option>
                            ))}
                        </select>
                    </div>

                    {/* Mode dropdown */}
                    <div className="flex flex-col gap-1">
                        <label className="text-xs text-slate-500">Exec Mode</label>
                        <select
                            value={filters.mode}
                            onChange={(e) => updateFilter('mode', e.target.value)}
                            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:border-copilot-500 focus:outline-none"
                        >
                            {modeOptions.map((opt) => (
                                <option key={opt.value} value={opt.value}>{opt.label}</option>
                            ))}
                        </select>
                    </div>

                    {/* Skill dropdown */}
                    {skills.length > 0 && (
                        <div className="flex flex-col gap-1">
                            <label className="text-xs text-slate-500">Skill</label>
                            <select
                                value={filters.skill_id}
                                onChange={(e) => updateFilter('skill_id', e.target.value)}
                                className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:border-copilot-500 focus:outline-none"
                            >
                                <option value="">All Skills</option>
                                {skills.map((skill) => (
                                    <option key={skill.id} value={skill.id}>{skill.name}</option>
                                ))}
                            </select>
                        </div>
                    )}

                    {/* Target input */}
                    <div className="flex flex-col gap-1">
                        <label className="text-xs text-slate-500">Target</label>
                        <input
                            type="text"
                            placeholder="container, VM..."
                            value={filters.target}
                            onChange={(e) => updateFilter('target', e.target.value)}
                            className="w-36 bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:border-copilot-500 focus:outline-none"
                        />
                    </div>

                    {/* Sort dropdown */}
                    <div className="flex flex-col gap-1 ml-auto">
                        <label className="text-xs text-slate-500">Sort</label>
                        <select
                            value={filters.sort}
                            onChange={(e) => updateFilter('sort', e.target.value as 'newest' | 'oldest_pending')}
                            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:border-copilot-500 focus:outline-none"
                        >
                            {sortOptions.map((opt) => (
                                <option key={opt.value} value={opt.value}>{opt.label}</option>
                            ))}
                        </select>
                    </div>
                </div>
            )}
        </div>
    );
}

// Active filter pills for showing what's currently filtered
interface ActiveFilterPillsProps {
    filters: FilterState;
    onChange: (filters: FilterState) => void;
}

export function ActiveFilterPills({ filters, onChange }: ActiveFilterPillsProps) {
    const pills: Array<{ key: keyof FilterState; label: string; value: string }> = [];

    if (filters.status !== 'all') {
        pills.push({ key: 'status', label: 'Status', value: filters.status.replace('_', ' ') });
    }
    if (filters.risk !== 'all') {
        pills.push({ key: 'risk', label: 'Risk', value: filters.risk });
    }
    if (filters.mode !== 'all') {
        pills.push({ key: 'mode', label: 'Mode', value: filters.mode });
    }
    if (filters.skill_id) {
        pills.push({ key: 'skill_id', label: 'Skill', value: filters.skill_id });
    }
    if (filters.target) {
        pills.push({ key: 'target', label: 'Target', value: filters.target });
    }
    if (filters.search) {
        pills.push({ key: 'search', label: 'Search', value: `"${filters.search}"` });
    }
    if (filters.needs_attention) {
        pills.push({ key: 'needs_attention', label: '', value: 'Needs Attention' });
    }

    if (pills.length === 0) return null;

    const removePill = (key: keyof FilterState) => {
        if (key === 'status' || key === 'risk' || key === 'mode') {
            onChange({ ...filters, [key]: 'all' });
        } else if (key === 'needs_attention') {
            onChange({ ...filters, [key]: false });
        } else {
            onChange({ ...filters, [key]: '' });
        }
    };

    return (
        <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-slate-500">Filtering by:</span>
            {pills.map((pill) => (
                <span
                    key={pill.key}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-copilot-500/20 text-copilot-400 text-xs"
                >
                    {pill.label && <span className="text-copilot-300">{pill.label}:</span>}
                    <span>{pill.value}</span>
                    <button
                        onClick={() => removePill(pill.key)}
                        className="ml-0.5 hover:text-white"
                    >
                        ✕
                    </button>
                </span>
            ))}
        </div>
    );
}

export { defaultFilters, showAllFilters };
export default FilterBar;
