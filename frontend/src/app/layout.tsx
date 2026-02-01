import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
    title: 'Homelab Copilot',
    description: 'Privacy-forward infrastructure copilot for homelabs',
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en">
            <body className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
                <div className="flex min-h-screen">
                    {/* Sidebar */}
                    <aside className="w-64 bg-slate-900/50 backdrop-blur-xl border-r border-slate-700/50 p-4">
                        <div className="flex items-center gap-3 mb-8">
                            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-copilot-400 to-copilot-600 flex items-center justify-center">
                                <span className="text-white text-xl">🏠</span>
                            </div>
                            <div>
                                <h1 className="text-white font-semibold">Homelab Copilot</h1>
                                <p className="text-slate-400 text-xs">Phase 0 • Scaffold</p>
                            </div>
                        </div>

                        <nav className="space-y-1">
                            <a
                                href="/"
                                className="flex items-center gap-3 px-3 py-2 rounded-lg text-white bg-copilot-600/20 border border-copilot-500/30"
                            >
                                <span>📊</span>
                                <span>Dashboard</span>
                            </a>
                            <a
                                href="#"
                                className="flex items-center gap-3 px-3 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/50 transition-colors"
                            >
                                <span>🖥️</span>
                                <span className="opacity-50">Inventory</span>
                                <span className="ml-auto text-xs bg-slate-700 px-2 py-0.5 rounded">Soon</span>
                            </a>
                            <a
                                href="#"
                                className="flex items-center gap-3 px-3 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/50 transition-colors"
                            >
                                <span>🚨</span>
                                <span className="opacity-50">Incidents</span>
                                <span className="ml-auto text-xs bg-slate-700 px-2 py-0.5 rounded">Soon</span>
                            </a>
                            <a
                                href="#"
                                className="flex items-center gap-3 px-3 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/50 transition-colors"
                            >
                                <span>📋</span>
                                <span className="opacity-50">Actions</span>
                                <span className="ml-auto text-xs bg-slate-700 px-2 py-0.5 rounded">Soon</span>
                            </a>
                        </nav>
                    </aside>

                    {/* Main Content */}
                    <main className="flex-1 p-8">{children}</main>
                </div>
            </body>
        </html>
    );
}
