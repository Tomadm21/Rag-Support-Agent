import { TrendingUp, TrendingDown, BarChart3, Brain, Clock, CheckCircle2 } from 'lucide-react';

interface Ticket {
    id: string;
    status: 'Open' | 'Draft Ready' | 'Sent' | 'Auto-Sent';
    sentiment?: 'Positive' | 'Neutral' | 'Negative';
    urgency?: 'Low' | 'Medium' | 'High' | 'Critical';
    category?: string;
    draft?: {
        confidence: number;
    };
}

interface AnalyticsDashboardProps {
    tickets: Ticket[];
}

export function AnalyticsDashboard({ tickets }: AnalyticsDashboardProps) {
    // Calculate metrics
    const totalTickets = tickets.length;
    const openTickets = tickets.filter(t => t.status === 'Open').length;
    const draftTickets = tickets.filter(t => t.status === 'Draft Ready').length;
    const sentTickets = tickets.filter(t => t.status === 'Sent' || t.status === 'Auto-Sent').length;
    const autoSentTickets = tickets.filter(t => t.status === 'Auto-Sent').length;

    // Resolution rate (sent / total)
    const resolutionRate = totalTickets > 0 ? (sentTickets / totalTickets) * 100 : 0;

    // Automation rate (auto-sent / sent)
    const automationRate = sentTickets > 0 ? (autoSentTickets / sentTickets) * 100 : 0;

    // Sentiment distribution
    const positiveSentiment = tickets.filter(t => t.sentiment === 'Positive').length;
    const neutralSentiment = tickets.filter(t => t.sentiment === 'Neutral').length;
    const negativeSentiment = tickets.filter(t => t.sentiment === 'Negative').length;

    // Confidence scores
    const ticketsWithDrafts = tickets.filter(t => t.draft);
    const avgConfidence = ticketsWithDrafts.length > 0
        ? (ticketsWithDrafts.reduce((acc, t) => acc + (t.draft?.confidence || 0), 0) / ticketsWithDrafts.length) * 100
        : 0;

    // High confidence drafts (>= 80%)
    const highConfidenceDrafts = ticketsWithDrafts.filter(t => (t.draft?.confidence || 0) >= 0.8).length;

    // Category breakdown
    const categories = ['Billing', 'Technical', 'Feature', 'Bug'];
    const categoryCount = categories.map(cat => ({
        name: cat,
        count: tickets.filter(t => t.category === cat).length
    }));

    // Urgency breakdown
    const criticalCount = tickets.filter(t => t.urgency === 'Critical').length;
    const highCount = tickets.filter(t => t.urgency === 'High').length;

    return (
        <div className="p-5 bg-zinc-900/30 border-b border-zinc-800">
            {/* Metrics Grid */}
            <div className="grid grid-cols-3 gap-3 mb-4">
                {/* Resolution Rate */}
                <div className="bg-zinc-900/50 rounded-lg p-3 border border-zinc-800">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-[10px] uppercase tracking-wider text-zinc-600">Resolution Rate</span>
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    </div>
                    <div className="flex items-baseline gap-2">
                        <span className="text-2xl font-bold text-emerald-400">{Math.round(resolutionRate)}%</span>
                        {resolutionRate >= 50 ? (
                            <TrendingUp className="w-3 h-3 text-emerald-400" />
                        ) : (
                            <TrendingDown className="w-3 h-3 text-red-400" />
                        )}
                    </div>
                    <p className="text-[10px] text-zinc-600 mt-1">{sentTickets}/{totalTickets} tickets resolved</p>
                </div>

                {/* AI Automation */}
                <div className="bg-zinc-900/50 rounded-lg p-3 border border-zinc-800">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-[10px] uppercase tracking-wider text-zinc-600">AI Automation</span>
                        <Brain className="w-3.5 h-3.5 text-violet-400" />
                    </div>
                    <div className="flex items-baseline gap-2">
                        <span className="text-2xl font-bold text-violet-400">{Math.round(automationRate)}%</span>
                        {automationRate >= 65 && <TrendingUp className="w-3 h-3 text-violet-400" />}
                    </div>
                    <p className="text-[10px] text-zinc-600 mt-1">{autoSentTickets} auto-sent tickets</p>
                </div>

                {/* Avg Confidence */}
                <div className="bg-zinc-900/50 rounded-lg p-3 border border-zinc-800">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-[10px] uppercase tracking-wider text-zinc-600">Avg Confidence</span>
                        <BarChart3 className="w-3.5 h-3.5 text-blue-400" />
                    </div>
                    <div className="flex items-baseline gap-2">
                        <span className={`text-2xl font-bold ${avgConfidence >= 80 ? 'text-emerald-400' : 'text-amber-400'}`}>
                            {Math.round(avgConfidence)}%
                        </span>
                    </div>
                    <p className="text-[10px] text-zinc-600 mt-1">{highConfidenceDrafts} high confidence</p>
                </div>
            </div>

            {/* Secondary Metrics Row */}
            <div className="grid grid-cols-2 gap-3">
                {/* Sentiment Distribution */}
                <div className="bg-zinc-900/50 rounded-lg p-3 border border-zinc-800">
                    <div className="flex items-center gap-2 mb-2">
                        <span className="text-[10px] uppercase tracking-wider text-zinc-600">Sentiment</span>
                    </div>
                    <div className="flex items-center gap-3">
                        <div className="flex items-center gap-1.5">
                            <span className="text-sm">😊</span>
                            <span className="text-xs text-emerald-400 font-medium">{positiveSentiment}</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                            <span className="text-sm">😐</span>
                            <span className="text-xs text-zinc-400 font-medium">{neutralSentiment}</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                            <span className="text-sm">😞</span>
                            <span className="text-xs text-red-400 font-medium">{negativeSentiment}</span>
                        </div>
                    </div>
                    {negativeSentiment > 0 && (
                        <p className="text-[9px] text-red-400/70 mt-2 flex items-center gap-1">
                            <Clock className="w-2.5 h-2.5" />
                            {negativeSentiment} ticket{negativeSentiment !== 1 ? 's' : ''} need attention
                        </p>
                    )}
                </div>

                {/* Category Breakdown */}
                <div className="bg-zinc-900/50 rounded-lg p-3 border border-zinc-800">
                    <div className="flex items-center gap-2 mb-2">
                        <span className="text-[10px] uppercase tracking-wider text-zinc-600">Categories</span>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                        {categoryCount.map(cat => (
                            <div key={cat.name} className="flex items-center justify-between">
                                <span className="text-[10px] text-zinc-500">{cat.name}</span>
                                <span className="text-xs text-zinc-300 font-medium">{cat.count}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Urgent Tickets Alert */}
            {(criticalCount > 0 || highCount > 0) && (
                <div className="mt-3 bg-red-500/10 border border-red-500/30 rounded-lg p-2.5 flex items-center gap-2">
                    <Clock className="w-3.5 h-3.5 text-red-400 shrink-0" />
                    <p className="text-[10px] text-red-400">
                        <span className="font-semibold">{criticalCount + highCount} urgent ticket{criticalCount + highCount !== 1 ? 's' : ''}</span>
                        {' '}require immediate attention
                        {criticalCount > 0 && <span className="ml-1">({criticalCount} critical)</span>}
                    </p>
                </div>
            )}
        </div>
    );
}
