'use client';

interface TimelineEvent {
    timestamp: string;
    label: string;
    type: 'created' | 'approved' | 'rejected' | 'executed' | 'completed' | 'failed';
    actor?: string;
    message?: string;
}

interface ExecutionTimelineProps {
    events: TimelineEvent[];
    className?: string;
}

const eventIcons: Record<string, string> = {
    created: '📝',
    approved: '✓',
    rejected: '✗',
    executed: '▶',
    completed: '✓',
    failed: '⚠',
};

const eventColors: Record<string, string> = {
    created: 'border-slate-600 bg-slate-800 text-slate-400',
    approved: 'border-emerald-500/50 bg-emerald-500/10 text-emerald-400',
    rejected: 'border-red-500/50 bg-red-500/10 text-red-400',
    executed: 'border-blue-500/50 bg-blue-500/10 text-blue-400',
    completed: 'border-emerald-500/50 bg-emerald-500/10 text-emerald-400',
    failed: 'border-red-500/50 bg-red-500/10 text-red-400',
};

export function ExecutionTimeline({ events, className = '' }: ExecutionTimelineProps) {
    if (events.length === 0) return null;

    return (
        <div className={`space-y-1 ${className}`}>
            {events.map((event, index) => (
                <div key={index} className="flex items-start gap-3">
                    {/* Timeline connector */}
                    <div className="flex flex-col items-center">
                        <div className={`w-8 h-8 flex items-center justify-center rounded-full border text-sm ${eventColors[event.type]}`}>
                            {eventIcons[event.type]}
                        </div>
                        {index < events.length - 1 && (
                            <div className="w-0.5 h-6 bg-slate-700" />
                        )}
                    </div>

                    {/* Event content */}
                    <div className="flex-1 pb-4">
                        <div className="flex items-center gap-2">
                            <span className="font-medium text-white text-sm">{event.label}</span>
                            {event.actor && (
                                <span className="text-xs text-slate-500">by {event.actor}</span>
                            )}
                        </div>
                        <div className="text-xs text-slate-400">
                            {new Date(event.timestamp).toLocaleString()}
                        </div>
                        {event.message && (
                            <div className="mt-1 text-sm text-slate-300">{event.message}</div>
                        )}
                    </div>
                </div>
            ))}
        </div>
    );
}

export function buildTimelineEvents(execution: {
    created_at: string;
    approved_at?: string;
    approved_by?: string;
    rejected_at?: string;
    rejected_by?: string;
    rejection_reason?: string;
    executed_at?: string;
    status: string;
    error_message?: string;
}): TimelineEvent[] {
    const events: TimelineEvent[] = [];

    // Created
    events.push({
        timestamp: execution.created_at,
        label: 'Created',
        type: 'created',
    });

    // Approved
    if (execution.approved_at) {
        events.push({
            timestamp: execution.approved_at,
            label: 'Approved',
            type: 'approved',
            actor: execution.approved_by,
        });
    }

    // Rejected
    if (execution.rejected_at) {
        events.push({
            timestamp: execution.rejected_at,
            label: 'Rejected',
            type: 'rejected',
            actor: execution.rejected_by,
            message: execution.rejection_reason,
        });
    }

    // Executed
    if (execution.executed_at) {
        events.push({
            timestamp: execution.executed_at,
            label: 'Executed',
            type: 'executed',
        });
    }

    // Completed/Failed
    if (execution.status === 'completed') {
        events.push({
            timestamp: execution.executed_at || execution.approved_at || execution.created_at,
            label: 'Completed',
            type: 'completed',
        });
    } else if (execution.status === 'failed') {
        events.push({
            timestamp: execution.executed_at || execution.created_at,
            label: 'Failed',
            type: 'failed',
            message: execution.error_message,
        });
    }

    return events;
}

export default ExecutionTimeline;
