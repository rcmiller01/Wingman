import type { Metadata } from 'next';
import './globals.css';

import { Sidebar } from '../components/layout/Sidebar';

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
            <body className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-slate-200">
                <div className="flex min-h-screen">
                    <Sidebar />
                    {/* Main Content */}
                    <main className="flex-1 p-8 overflow-y-auto h-screen">{children}</main>
                </div>
            </body>
        </html>
    );
}

{/* Main Content */ }
<main className="flex-1 p-8">{children}</main>
                </div >
            </body >
        </html >
    );
}
