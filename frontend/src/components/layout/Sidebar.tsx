'use client';
import { usePathname } from 'next/navigation';
import Link from 'next/link';

export function Sidebar() {
    const pathname = usePathname();

    const isActive = (path: string) => {
        if (path === '/') return pathname === '/';
        return pathname.startsWith(path);
    };

    return (
        <aside className="w-64 bg-slate-900/50 backdrop-blur-xl border-r border-slate-700/50 p-4 flex flex-col shrink-0">
            <div className="flex items-center gap-3 mb-8">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-copilot-400 to-copilot-600 flex items-center justify-center shadow-lg shadow-copilot-500/20">
                    <span className="text-white text-xl">🏠</span>
                </div>
                <div>
                    <h1 className="text-white font-semibold">Homelab Copilot</h1>
                    <p className="text-slate-400 text-xs">Phase 5 • Memory + RAG</p>
                </div>
            </div>

            <nav className="space-y-1">
                <NavLink href="/" icon="📊" label="Dashboard" active={isActive('/')} />
                <NavLink href="/inventory" icon="🖥️" label="Inventory" active={isActive('/inventory')} />
                <NavLink href="/incidents" icon="🚨" label="Incidents" active={isActive('/incidents')} />
                <NavLink href="/executions" icon="⚡" label="Executions" active={isActive('/executions')} />
                <NavLink href="/actions" icon="📋" label="Actions" active={isActive('/actions')} />
                <NavLink href="/settings" icon="⚙️" label="Settings" active={isActive('/settings')} />
            </nav>

            <div className="mt-auto pt-8 border-t border-slate-800">
                <div className="bg-slate-800/50 rounded-lg p-3">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                        <span className="text-xs font-medium text-slate-300">System Healthy</span>
                    </div>
                    <div className="text-[10px] text-slate-500 font-mono">
                        v0.3.0-alpha
                    </div>
                </div>
            </div>
        </aside>
    );
}

function NavLink({ href, icon, label, active, soon }: { href: string; icon: string; label: string; active?: boolean; soon?: boolean }) {
    return (
        <Link
            href={href}
            className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-200 ${active
                    ? 'bg-copilot-600/20 text-white border border-copilot-500/30 shadow-sm'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                } ${soon ? 'cursor-not-allowed opacity-60' : ''}`}
            onClick={(e) => soon && e.preventDefault()}
        >
            <span>{icon}</span>
            <span>{label}</span>
        </Link>
    );
}
