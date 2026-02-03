'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { getApiUrl } from '@/utils/api';

interface SkillSummary {
    id: string;
    title: string;
    tier: number;
    category: string;
    risk: string;
    short_description: string;
    file_path: string;
    applies_to: {
        subsystems: string[];
        signatures: string[];
        resource_types: string[];
    };
}

interface SkillDetail {
    meta: {
        id: string;
        title: string;
        tier: number;
        category: string;
        risk: string;
        short_description: string;
        version?: string | null;
        applies_to: {
            subsystems: string[];
            signatures: string[];
            resource_types: string[];
        };
        outputs: string[];
    };
    inputs: Array<{
        name: string;
        type: string;
        required: boolean;
        description: string;
        default?: string | number | boolean | null;
    }>;
    sections: Record<string, string>;
    file_path: string;
}

export default function SkillsLibraryPage() {
    const searchParams = useSearchParams();
    const preselectedId = searchParams.get('selected');
    const [skills, setSkills] = useState<SkillSummary[]>([]);
    const [selectedId, setSelectedId] = useState<string | null>(preselectedId);
    const [selectedSkill, setSelectedSkill] = useState<SkillDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [filters, setFilters] = useState({ category: 'all', risk: 'all', tier: 'all', query: '' });

    useEffect(() => {
        async function fetchSkills() {
            try {
                const res = await fetch(getApiUrl('/skills'));
                const data = await res.json();
                setSkills(data.skills || []);
                if (!selectedId && data.skills?.length) {
                    setSelectedId(data.skills[0].id);
                }
            } catch (err) {
                console.error('Failed to load skills', err);
            } finally {
                setLoading(false);
            }
        }
        fetchSkills();
    }, []);

    useEffect(() => {
        if (!selectedId) {
            setSelectedSkill(null);
            return;
        }
        async function fetchSkillDetail() {
            try {
                const res = await fetch(getApiUrl(`/skills/${selectedId}`));
                if (!res.ok) throw new Error('Failed to fetch skill');
                const data = await res.json();
                setSelectedSkill(data);
            } catch (err) {
                console.error('Failed to load skill detail', err);
            }
        }
        fetchSkillDetail();
    }, [selectedId]);

    const filteredSkills = useMemo(() => {
        return skills.filter(skill => {
            if (filters.category !== 'all' && skill.category !== filters.category) return false;
            if (filters.risk !== 'all' && skill.risk !== filters.risk) return false;
            if (filters.tier !== 'all' && String(skill.tier) !== filters.tier) return false;
            if (filters.query) {
                const needle = filters.query.toLowerCase();
                if (!skill.title.toLowerCase().includes(needle) && !skill.short_description.toLowerCase().includes(needle)) {
                    return false;
                }
            }
            return true;
        });
    }, [skills, filters]);

    const categories = Array.from(new Set(skills.map(skill => skill.category)));
    const risks = Array.from(new Set(skills.map(skill => skill.risk)));
    const tiers = Array.from(new Set(skills.map(skill => String(skill.tier))));

    if (loading) {
        return (
            <div className="max-w-5xl mx-auto space-y-6 animate-pulse">
                <div className="h-8 bg-slate-800 rounded w-1/3" />
                <div className="h-72 bg-slate-800 rounded" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <header className="space-y-2">
                <h1 className="text-3xl font-bold text-white">Skills Library</h1>
                <p className="text-slate-400">Browse Tier 1 and Tier 2 skills. Wingman only provides plans and commands.</p>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-6">
                <aside className="space-y-4">
                    <div className="bg-slate-900/60 border border-slate-700/50 rounded-xl p-4 space-y-3">
                        <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Filters</h2>
                        <input
                            type="text"
                            placeholder="Search skills"
                            value={filters.query}
                            onChange={event => setFilters({ ...filters, query: event.target.value })}
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100"
                        />
                        <div className="grid gap-3">
                            <FilterSelect
                                label="Category"
                                value={filters.category}
                                options={['all', ...categories]}
                                onChange={value => setFilters({ ...filters, category: value })}
                            />
                            <FilterSelect
                                label="Risk"
                                value={filters.risk}
                                options={['all', ...risks]}
                                onChange={value => setFilters({ ...filters, risk: value })}
                            />
                            <FilterSelect
                                label="Tier"
                                value={filters.tier}
                                options={['all', ...tiers]}
                                onChange={value => setFilters({ ...filters, tier: value })}
                            />
                        </div>
                    </div>

                    <div className="space-y-2">
                        {filteredSkills.length === 0 && (
                            <div className="text-slate-500 text-sm">No skills match the selected filters.</div>
                        )}
                        {filteredSkills.map(skill => (
                            <button
                                key={skill.id}
                                onClick={() => setSelectedId(skill.id)}
                                className={`w-full text-left rounded-xl border px-4 py-3 transition-all ${
                                    selectedId === skill.id
                                        ? 'border-copilot-400 bg-copilot-600/10'
                                        : 'border-slate-700/50 bg-slate-900/40 hover:border-slate-600'
                                }`}
                            >
                                <div className="flex items-center justify-between">
                                    <h3 className="text-white font-semibold text-sm">{skill.title}</h3>
                                    <span className="text-xs text-slate-400">Tier {skill.tier}</span>
                                </div>
                                <p className="text-xs text-slate-400 mt-1">{skill.short_description}</p>
                                <div className="flex items-center gap-2 mt-2 text-[10px] uppercase tracking-wider text-slate-500">
                                    <span>{skill.category}</span>
                                    <span>•</span>
                                    <span>{skill.risk}</span>
                                </div>
                            </button>
                        ))}
                    </div>
                </aside>

                <section className="bg-slate-900/50 border border-slate-700/50 rounded-xl p-6 space-y-6">
                    {selectedSkill ? (
                        <>
                            <div className="flex items-start justify-between gap-4">
                                <div>
                                    <h2 className="text-2xl font-semibold text-white">{selectedSkill.meta.title}</h2>
                                    <p className="text-slate-400 mt-1">{selectedSkill.meta.short_description}</p>
                                    <div className="flex flex-wrap gap-2 mt-3">
                                        <Badge>{selectedSkill.meta.category}</Badge>
                                        <Badge>Tier {selectedSkill.meta.tier}</Badge>
                                        <Badge>{selectedSkill.meta.risk}</Badge>
                                    </div>
                                </div>
                                <Link
                                    href={`/chat?command=${encodeURIComponent(`run skill ${selectedSkill.meta.id}`)}`}
                                    className="bg-copilot-500/20 text-copilot-200 border border-copilot-500/40 px-4 py-2 rounded-lg text-sm"
                                >
                                    Run in chat
                                </Link>
                            </div>

                            <div className="grid md:grid-cols-2 gap-4 text-sm text-slate-300">
                                <div>
                                    <h4 className="text-xs uppercase tracking-wider text-slate-500">Applies To</h4>
                                    <p>Subsystems: {selectedSkill.meta.applies_to.subsystems.join(', ') || '—'}</p>
                                    <p>Signatures: {selectedSkill.meta.applies_to.signatures.join(', ') || '—'}</p>
                                    <p>Resource types: {selectedSkill.meta.applies_to.resource_types.join(', ') || '—'}</p>
                                </div>
                                <div>
                                    <h4 className="text-xs uppercase tracking-wider text-slate-500">Outputs</h4>
                                    <p>{selectedSkill.meta.outputs.join(', ') || 'plan'}</p>
                                    <p className="text-slate-500 text-xs mt-2">File: {selectedSkill.file_path}</p>
                                </div>
                            </div>

                            <div className="space-y-3">
                                <h3 className="text-sm uppercase tracking-wider text-slate-500">Inputs</h3>
                                {selectedSkill.inputs.length > 0 ? (
                                    <ul className="space-y-2">
                                        {selectedSkill.inputs.map(input => (
                                            <li key={input.name} className="text-sm text-slate-300">
                                                <span className="font-semibold text-white">{input.name}</span> ({input.type}){' '}
                                                {input.required ? 'required' : 'optional'} — {input.description}
                                            </li>
                                        ))}
                                    </ul>
                                ) : (
                                    <p className="text-slate-500 text-sm">No inputs required.</p>
                                )}
                            </div>

                            <div className="space-y-3">
                                <h3 className="text-sm uppercase tracking-wider text-slate-500">Sections</h3>
                                <div className="space-y-3">
                                    {Object.entries(selectedSkill.sections).map(([title, content]) => (
                                        <details key={title} className="rounded-lg border border-slate-700/60 bg-slate-900/40 p-3">
                                            <summary className="cursor-pointer text-slate-200 font-medium">{title}</summary>
                                            <pre className="whitespace-pre-wrap text-xs text-slate-400 mt-2 font-sans">{content}</pre>
                                        </details>
                                    ))}
                                </div>
                            </div>
                        </>
                    ) : (
                        <p className="text-slate-500">Select a skill to view details.</p>
                    )}
                </section>
            </div>
        </div>
    );
}

function FilterSelect({
    label,
    value,
    options,
    onChange,
}: {
    label: string;
    value: string;
    options: string[];
    onChange: (value: string) => void;
}) {
    return (
        <label className="text-xs text-slate-400">
            {label}
            <select
                value={value}
                onChange={event => onChange(event.target.value)}
                className="mt-1 w-full bg-slate-900 border border-slate-700 rounded-lg px-2 py-2 text-sm text-slate-100"
            >
                {options.map(option => (
                    <option key={option} value={option}>
                        {option}
                    </option>
                ))}
            </select>
        </label>
    );
}

function Badge({ children }: { children: React.ReactNode }) {
    return <span className="px-2 py-1 rounded-full bg-slate-800 text-xs text-slate-200">{children}</span>;
}
