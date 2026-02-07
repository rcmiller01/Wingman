'use client';

interface LogViewerProps {
    resourceRef: string;
    height?: string;
}

export function LogViewer({ resourceRef, height = 'h-[400px]' }: LogViewerProps) {
    return (
        <div className={`${height} overflow-auto bg-slate-900 rounded-lg p-4 font-mono text-sm`}>
            <p className="text-slate-400">Log viewer for {resourceRef}</p>
            <p className="text-slate-500 text-xs mt-2">Logs will appear here once collection begins.</p>
        </div>
    );
}
