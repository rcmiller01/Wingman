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
}

interface SkillDetail {
    meta: {
        id: string;
        title: string;
        tier: number;
        category: string;
        risk: string;
        short_description: string;
        outputs: string[];
    };
    inputs: Array<{
        name: string;
        type: string;
        required: boolean;
        description: string;
    }>;
    sections: Record<string, string>;
}

interface RenderedPlan {
    resolved_inputs: Record<string, string | number | boolean>;
    plan_markdown: string;
    commands: string;
    tofu?: string | null;
}

interface Message {
    id: string;
    role: 'user' | 'assistant';
    content?: string;
    list?: SkillSummary[];
    skill?: SkillDetail;
    rendered?: RenderedPlan;
}

interface PendingRun {
    skill: SkillDetail;
    requiredInputs: SkillDetail['inputs'];
    collected: Record<string, string | number | boolean>;
    nextIndex: number;
}

export default function ChatPage() {
    const searchParams = useSearchParams();
    const [messages, setMessages] = useState<Message[]>([]);
    const [inputValue, setInputValue] = useState('');
    const [pendingRun, setPendingRun] = useState<PendingRun | null>(null);

    const nextPrompt = useMemo(() => {
        if (!pendingRun) return null;
        return pendingRun.requiredInputs[pendingRun.nextIndex] || null;
    }, [pendingRun]);

    useEffect(() => {
        const command = searchParams.get('command');
        if (command) {
            handleCommand(command);
        }
    }, []);

    const appendMessage = (message: Message) => {
        setMessages(prev => [...prev, message]);
    };

    const handleSubmit = async (event: React.FormEvent) => {
        event.preventDefault();
        if (!inputValue.trim()) return;
        const text = inputValue.trim();
        setInputValue('');

        if (nextPrompt) {
            appendMessage({ id: crypto.randomUUID(), role: 'user', content: text });
            await handlePromptResponse(text);
            return;
        }

        await handleCommand(text);
    };

    const handleCommand = async (text: string) => {
        appendMessage({ id: crypto.randomUUID(), role: 'user', content: text });
        const lower = text.toLowerCase();

        if (lower.startsWith('list skills')) {
            const query = text.slice('list skills'.length).trim();
            await listSkills(query);
            return;
        }

        if (lower.startsWith('show skill')) {
            const id = text.slice('show skill'.length).trim();
            if (!id) {
                appendMessage({ id: crypto.randomUUID(), role: 'assistant', content: 'Provide a skill id, e.g. show skill proxmox-node-health.' });
                return;
            }
            await showSkill(id);
            return;
        }

        if (lower.startsWith('run skill')) {
            const id = text.slice('run skill'.length).trim();
            if (!id) {
                appendMessage({ id: crypto.randomUUID(), role: 'assistant', content: 'Provide a skill id, e.g. run skill proxmox-node-health.' });
                return;
            }
            await startRunSkill(id);
            return;
        }

        appendMessage({
            id: crypto.randomUUID(),
            role: 'assistant',
            content: 'Unknown command. Try: list skills, show skill <id>, or run skill <id>.',
        });
    };

    const listSkills = async (query: string) => {
        try {
            const res = await fetch(getApiUrl(`/skills${query ? `?q=${encodeURIComponent(query)}` : ''}`));
            const data = await res.json();
            const skills = (data.skills || []).slice(0, 5);
            appendMessage({
                id: crypto.randomUUID(),
                role: 'assistant',
                list: skills,
                content: skills.length ? 'Top matching skills:' : 'No skills matched that filter.',
            });
        } catch (err) {
            appendMessage({ id: crypto.randomUUID(), role: 'assistant', content: 'Failed to fetch skills.' });
        }
    };

    const showSkill = async (id: string) => {
        try {
            const res = await fetch(getApiUrl(`/skills/${id}`));
            if (!res.ok) throw new Error('Skill not found');
            const data = await res.json();
            appendMessage({ id: crypto.randomUUID(), role: 'assistant', skill: data });
        } catch (err) {
            appendMessage({ id: crypto.randomUUID(), role: 'assistant', content: 'Skill not found.' });
        }
    };

    const startRunSkill = async (id: string) => {
        try {
            const res = await fetch(getApiUrl(`/skills/${id}`));
            if (!res.ok) throw new Error('Skill not found');
            const data: SkillDetail = await res.json();
            const requiredInputs = data.inputs.filter(input => input.required);
            if (requiredInputs.length === 0) {
                await renderSkill(data, {});
                return;
            }
            setPendingRun({ skill: data, requiredInputs, collected: {}, nextIndex: 0 });
            appendMessage({
                id: crypto.randomUUID(),
                role: 'assistant',
                content: `Provide ${requiredInputs[0].name} (${requiredInputs[0].type}).`,
            });
        } catch (err) {
            appendMessage({ id: crypto.randomUUID(), role: 'assistant', content: 'Skill not found.' });
        }
    };

    const handlePromptResponse = async (text: string) => {
        if (!pendingRun || !nextPrompt) return;
        const coerced = coerceInputValue(nextPrompt, text);
        if (coerced === null) {
            appendMessage({
                id: crypto.randomUUID(),
                role: 'assistant',
                content: `Invalid value for ${nextPrompt.name}. Please provide a ${nextPrompt.type}.`,
            });
            return;
        }
        const updated = {
            ...pendingRun,
            collected: { ...pendingRun.collected, [nextPrompt.name]: coerced },
            nextIndex: pendingRun.nextIndex + 1,
        };

        if (updated.nextIndex >= updated.requiredInputs.length) {
            setPendingRun(null);
            await renderSkill(updated.skill, updated.collected);
            return;
        }

        setPendingRun(updated);
        const upcoming = updated.requiredInputs[updated.nextIndex];
        appendMessage({
            id: crypto.randomUUID(),
            role: 'assistant',
            content: `Provide ${upcoming.name} (${upcoming.type}).`,
        });
    };

    const renderSkill = async (skill: SkillDetail, inputs: Record<string, string | number | boolean>) => {
        try {
            const res = await fetch(getApiUrl(`/skills/${skill.meta.id}/render`), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ inputs }),
            });
            if (!res.ok) {
                const error = await res.json();
                throw new Error(error.detail || 'Render failed');
            }
            const data = await res.json();
            appendMessage({ id: crypto.randomUUID(), role: 'assistant', rendered: data });
        } catch (err: any) {
            appendMessage({ id: crypto.randomUUID(), role: 'assistant', content: err.message || 'Render failed.' });
        }
    };

    return (
        <div className="max-w-4xl mx-auto space-y-6">
            <header className="space-y-1">
                <h1 className="text-3xl font-bold text-white">Chat</h1>
                <p className="text-slate-400">Use chat commands to list, show, or run Tier 1/2 skills.</p>
            </header>

            <div className="space-y-4">
                {messages.length === 0 && (
                    <div className="text-slate-500 text-sm">Try: list skills, show skill proxmox-node-health, run skill proxmox-node-health.</div>
                )}
                {messages.map(message => (
                    <div key={message.id} className={`rounded-lg px-4 py-3 ${message.role === 'user' ? 'bg-slate-800/60 text-slate-200' : 'bg-slate-900/60 text-slate-100'}`}>
                        {message.content && <p className="text-sm whitespace-pre-wrap">{message.content}</p>}
                        {message.list && (
                            <div className="mt-3 space-y-2">
                                {message.list.map(skill => (
                                    <div key={skill.id} className="border border-slate-700/60 rounded-lg p-3">
                                        <div className="flex items-center justify-between">
                                            <h4 className="text-sm font-semibold">{skill.title}</h4>
                                            <span className="text-xs text-slate-400">Tier {skill.tier}</span>
                                        </div>
                                        <p className="text-xs text-slate-400 mt-1">{skill.short_description}</p>
                                        <div className="flex items-center gap-2 mt-2 text-[10px] uppercase tracking-wider text-slate-500">
                                            <span>{skill.category}</span>
                                            <span>•</span>
                                            <span>{skill.risk}</span>
                                        </div>
                                    </div>
                                ))}
                                <Link href="/skills" className="text-xs text-copilot-300">View full library →</Link>
                            </div>
                        )}
                        {message.skill && (
                            <div className="mt-2 space-y-2">
                                <h4 className="text-sm font-semibold">{message.skill.meta.title}</h4>
                                <p className="text-xs text-slate-400">{message.skill.meta.short_description}</p>
                                <div className="flex flex-wrap gap-2 text-[10px] uppercase tracking-wider text-slate-500">
                                    <span>{message.skill.meta.category}</span>
                                    <span>Tier {message.skill.meta.tier}</span>
                                    <span>{message.skill.meta.risk}</span>
                                </div>
                                <div className="text-xs text-slate-500">Sections: {Object.keys(message.skill.sections).join(', ')}</div>
                            </div>
                        )}
                        {message.rendered && (
                            <div className="mt-3 space-y-4 text-sm">
                                <div className="border border-yellow-500/40 bg-yellow-500/10 text-yellow-200 px-3 py-2 rounded-lg text-xs">
                                    Wingman does not execute commands. Review and run them yourself.
                                </div>
                                <section>
                                    <h4 className="text-xs uppercase tracking-wider text-slate-500">Plan</h4>
                                    <pre className="whitespace-pre-wrap text-xs text-slate-300 mt-2 font-sans">{message.rendered.plan_markdown}</pre>
                                </section>
                                <section>
                                    <div className="flex items-center justify-between">
                                        <h4 className="text-xs uppercase tracking-wider text-slate-500">Commands</h4>
                                        <CopyButton text={message.rendered.commands} />
                                    </div>
                                    <pre className="whitespace-pre-wrap text-xs text-slate-300 mt-2 font-mono">{message.rendered.commands}</pre>
                                </section>
                                {message.rendered.tofu && (
                                    <section>
                                        <div className="flex items-center justify-between">
                                            <h4 className="text-xs uppercase tracking-wider text-slate-500">OpenTofu</h4>
                                            <CopyButton text={message.rendered.tofu} />
                                        </div>
                                        <pre className="whitespace-pre-wrap text-xs text-slate-300 mt-2 font-mono">{message.rendered.tofu}</pre>
                                    </section>
                                )}
                            </div>
                        )}
                    </div>
                ))}
            </div>

            <form onSubmit={handleSubmit} className="flex items-center gap-3">
                <input
                    type="text"
                    value={inputValue}
                    onChange={event => setInputValue(event.target.value)}
                    placeholder={nextPrompt ? `Enter ${nextPrompt.name}` : 'Type a command...'}
                    className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-sm text-slate-100"
                />
                <button
                    type="submit"
                    className="bg-copilot-500/20 border border-copilot-500/40 text-copilot-200 px-4 py-2 rounded-lg text-sm"
                >
                    Send
                </button>
            </form>
        </div>
    );
}

function coerceInputValue(input: SkillDetail['inputs'][0], raw: string): string | number | boolean | null {
    if (input.type === 'boolean') {
        if (raw.toLowerCase() === 'true') return true;
        if (raw.toLowerCase() === 'false') return false;
        return null;
    }
    if (input.type === 'integer') {
        const parsed = Number.parseInt(raw, 10);
        return Number.isNaN(parsed) ? null : parsed;
    }
    if (input.type === 'number') {
        const parsed = Number.parseFloat(raw);
        return Number.isNaN(parsed) ? null : parsed;
    }
    return raw;
}

function CopyButton({ text }: { text: string }) {
    const [copied, setCopied] = useState(false);

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(text);
            setCopied(true);
            setTimeout(() => setCopied(false), 1500);
        } catch (err) {
            setCopied(false);
        }
    };

    return (
        <button
            type="button"
            onClick={handleCopy}
            className="text-xs text-copilot-200 border border-copilot-500/40 px-2 py-1 rounded"
        >
            {copied ? 'Copied' : 'Copy'}
        </button>
    );
}
