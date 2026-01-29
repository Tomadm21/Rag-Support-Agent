import { useState } from 'react';
import { useCopilotReadable } from "@copilotkit/react-core";
import {
    Send,
    ChevronDown,
    ChevronUp,
    CheckCircle,
    AlertTriangle,
    Bot,
    User,
    Loader2,
    Sparkles,
    Clock,
    Edit3,
    X,
    Inbox,
    Mail,
    FileText,
    Database,
    BookOpen
} from 'lucide-react';
import { AnalyticsDashboard } from '../Analytics/AnalyticsDashboard';
import { RAGSourceSelector } from '../RAGSourceSelector/RAGSourceSelector';

// Types
interface RAGSource {
    document: string;
    section: string;
    category: string;
    relevance: number;
    content_preview?: string;
}

interface TicketDraft {
    text: string;
    confidence: number;
    critique: string;
    needsHumanReview: boolean;
    generatedAt: Date;
    ragSources?: RAGSource[];
}

interface Ticket {
    id: string;
    subject: string;
    customer: string;
    query: string;
    status: 'Open' | 'Draft Ready' | 'Sent' | 'Auto-Sent';
    category?: string;
    sentiment?: 'Positive' | 'Neutral' | 'Negative';
    urgency?: 'Low' | 'Medium' | 'High' | 'Critical';
    draft?: TicketDraft;
    sentAt?: Date;
    sentBy?: 'human' | 'ai';
}

// Initial tickets
const INITIAL_TICKETS: Ticket[] = [
    {
        id: "T-101",
        subject: "Refund Request",
        customer: "alice@example.com",
        query: "I was charged twice for the premium plan. Please refund the duplicate charge immediately.",
        status: 'Open'
    },
    {
        id: "T-102",
        subject: "API 500 Error",
        customer: "dev@startup.io",
        query: "Our integration is failing with a 500 error on the /v1/users endpoint since this morning.",
        status: 'Open'
    },
    {
        id: "T-103",
        subject: "Feature Request",
        customer: "pm@enterprise.com",
        query: "We would love to have a bulk export feature for our analytics dashboard. Is this on the roadmap?",
        status: 'Open'
    },
    {
        id: "T-104",
        subject: "Login Issues",
        customer: "user@gmail.com",
        query: "I can't log into my account. I've tried resetting my password but I'm not receiving the reset email.",
        status: 'Open'
    }
];

export function TicketEditor() {
    const [tickets, setTickets] = useState<Ticket[]>(INITIAL_TICKETS);
    const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);
    const [expandedTickets, setExpandedTickets] = useState<Set<string>>(new Set());
    const [editingTicketId, setEditingTicketId] = useState<string | null>(null);
    const [editDraft, setEditDraft] = useState("");
    const [processingTickets, setProcessingTickets] = useState<Set<string>>(new Set());
    const [sendingTickets, setSendingTickets] = useState<Set<string>>(new Set());
    const [showSourceSelector, setShowSourceSelector] = useState<Set<string>>(new Set());
    const [suggestedSources, setSuggestedSources] = useState<Map<string, RAGSource[]>>(new Map());
    const [isDetailCollapsed, setIsDetailCollapsed] = useState(false);

    const selectedTicket = tickets.find(t => t.id === selectedTicketId) || null;

    // Provide context to CopilotKit
    useCopilotReadable({
        description: "All support tickets with their current status and drafts",
        value: tickets,
    });

    useCopilotReadable({
        description: "The currently selected ticket for detailed view",
        value: selectedTicket,
    });

    // Fetch suggested sources for a ticket
    const fetchSuggestedSources = async (ticketId: string) => {
        const ticket = tickets.find(t => t.id === ticketId);
        if (!ticket || ticket.status !== 'Open') return;

        try {
            const response = await fetch('/api/suggest-sources', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model: 'gpt-4',
                    messages: [{ role: 'user', content: ticket.query }]
                })
            });

            const data = await response.json();
            const sources = data.suggested_sources || [];

            setSuggestedSources(prev => {
                const next = new Map(prev);
                next.set(ticketId, sources);
                return next;
            });
        } catch (error) {
            console.error('Error fetching suggested sources:', error);
        }
    };

    // Toggle expand/collapse for a ticket
    const toggleExpand = (ticketId: string, e: React.MouseEvent) => {
        e.stopPropagation();
        setExpandedTickets(prev => {
            const next = new Set(prev);
            if (next.has(ticketId)) {
                next.delete(ticketId);
            } else {
                next.add(ticketId);
                // Fetch suggested sources when expanding an Open ticket
                const ticket = tickets.find(t => t.id === ticketId);
                if (ticket?.status === 'Open' && !suggestedSources.has(ticketId)) {
                    fetchSuggestedSources(ticketId);
                }
            }
            return next;
        });
    };

    // Handle ticket selection
    const handleSelectTicket = (ticketId: string) => {
        setSelectedTicketId(ticketId);
        // Fetch suggested sources for Open tickets
        const ticket = tickets.find(t => t.id === ticketId);
        if (ticket?.status === 'Open' && !suggestedSources.has(ticketId)) {
            fetchSuggestedSources(ticketId);
        }
    };

    // Generate draft for a ticket
    const generateDraft = async (ticketId: string, selectedSources?: string[]) => {
        const ticket = tickets.find(t => t.id === ticketId);
        if (!ticket) return;

        setProcessingTickets(prev => new Set(prev).add(ticketId));

        try {
            // Build request with optional source selection
            const requestBody: any = {
                model: 'gpt-4',
                messages: [{ role: 'user', content: ticket.query }],
                stream: false
            };

            // Add selected sources if provided
            if (selectedSources && selectedSources.length > 0) {
                requestBody.selected_sources = selectedSources;
            }

            const response = await fetch('/api/copilot', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });

            const data = await response.json();
            const draftText = data.choices?.[0]?.message?.content || '';

            // Get metadata from response (or use defaults)
            const metadata = data.metadata || {};
            const confidence = metadata.confidence ?? 0.85;
            const critique = metadata.critique || '';
            const ragSources = metadata.rag_sources || [];
            const category = metadata.category || ticket.category;
            const sentiment = metadata.sentiment || 'Neutral';
            const urgency = metadata.urgency || 'Medium';

            // The draft text is already clean from the backend
            const cleanDraft = draftText.trim();

            const newDraft: TicketDraft = {
                text: cleanDraft,
                confidence,
                critique,
                needsHumanReview: confidence < 0.8,
                generatedAt: new Date(),
                ragSources
            };

            setTickets(prev => prev.map(t =>
                t.id === ticketId
                    ? {
                        ...t,
                        draft: newDraft,
                        status: 'Draft Ready' as const,
                        category,
                        sentiment: sentiment as 'Positive' | 'Neutral' | 'Negative',
                        urgency: urgency as 'Low' | 'Medium' | 'High' | 'Critical'
                    }
                    : t
            ));

            // Auto-expand to show the draft
            setExpandedTickets(prev => new Set(prev).add(ticketId));

            // Hide source selector after generation
            setShowSourceSelector(prev => {
                const next = new Set(prev);
                next.delete(ticketId);
                return next;
            });

            // Auto-send if confidence is high enough
            if (confidence >= 0.9) {
                setTimeout(() => autoSendDraft(ticketId), 1500);
            }

        } catch (error) {
            console.error('Error generating draft:', error);
        } finally {
            setProcessingTickets(prev => {
                const next = new Set(prev);
                next.delete(ticketId);
                return next;
            });
        }
    };

    // Auto-send draft (for high confidence)
    const autoSendDraft = async (ticketId: string) => {
        const ticket = tickets.find(t => t.id === ticketId);
        if (!ticket?.draft || ticket.status === 'Sent' || ticket.status === 'Auto-Sent') return;

        setSendingTickets(prev => new Set(prev).add(ticketId));

        // Simulate sending
        await new Promise(resolve => setTimeout(resolve, 1000));

        setTickets(prev => prev.map(t =>
            t.id === ticketId
                ? { ...t, status: 'Auto-Sent' as const, sentAt: new Date(), sentBy: 'ai' as const }
                : t
        ));

        setSendingTickets(prev => {
            const next = new Set(prev);
            next.delete(ticketId);
            return next;
        });
    };

    // Manual send draft
    const sendDraft = async (ticketId: string, e: React.MouseEvent) => {
        e.stopPropagation();
        const ticket = tickets.find(t => t.id === ticketId);
        if (!ticket?.draft) return;

        setSendingTickets(prev => new Set(prev).add(ticketId));

        // Simulate sending
        await new Promise(resolve => setTimeout(resolve, 800));

        setTickets(prev => prev.map(t =>
            t.id === ticketId
                ? { ...t, status: 'Sent' as const, sentAt: new Date(), sentBy: 'human' as const }
                : t
        ));

        setSendingTickets(prev => {
            const next = new Set(prev);
            next.delete(ticketId);
            return next;
        });

        if (editingTicketId === ticketId) {
            setEditingTicketId(null);
        }
    };

    // Open edit mode
    const openEditor = (ticketId: string) => {
        const ticket = tickets.find(t => t.id === ticketId);
        if (ticket?.draft) {
            setEditingTicketId(ticketId);
            setEditDraft(ticket.draft.text);
            setSelectedTicketId(ticketId);
        }
    };

    // Save edited draft
    const saveEdit = () => {
        if (!editingTicketId) return;

        setTickets(prev => prev.map(t =>
            t.id === editingTicketId && t.draft
                ? { ...t, draft: { ...t.draft, text: editDraft } }
                : t
        ));
        setEditingTicketId(null);
    };

    // Get status badge style
    const getStatusBadge = (ticket: Ticket) => {
        switch (ticket.status) {
            case 'Open':
                return 'bg-amber-500/20 text-amber-400 border border-amber-500/30';
            case 'Draft Ready':
                return 'bg-blue-500/20 text-blue-400 border border-blue-500/30';
            case 'Sent':
                return 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30';
            case 'Auto-Sent':
                return 'bg-violet-500/20 text-violet-400 border border-violet-500/30';
            default:
                return 'bg-zinc-700 text-zinc-400';
        }
    };

    // Get sentiment emoji
    const getSentimentEmoji = (sentiment?: string) => {
        switch (sentiment) {
            case 'Positive':
                return '😊';
            case 'Negative':
                return '😞';
            case 'Neutral':
            default:
                return '😐';
        }
    };

    // Get urgency badge style
    const getUrgencyBadge = (urgency?: string) => {
        switch (urgency) {
            case 'Critical':
                return { style: 'bg-red-500/20 text-red-400 border border-red-500/30', label: 'CRITICAL' };
            case 'High':
                return { style: 'bg-orange-500/20 text-orange-400 border border-orange-500/30', label: 'High' };
            case 'Low':
                return { style: 'bg-zinc-700/20 text-zinc-500 border border-zinc-700/30', label: 'Low' };
            case 'Medium':
            default:
                return { style: 'bg-zinc-600/20 text-zinc-400 border border-zinc-600/30', label: 'Medium' };
        }
    };

    // Render ticket card in sidebar
    const renderTicketCard = (ticket: Ticket) => {
        const isExpanded = expandedTickets.has(ticket.id);
        const isProcessing = processingTickets.has(ticket.id);
        const isSending = sendingTickets.has(ticket.id);
        const hasDraft = !!ticket.draft;
        const isSent = ticket.status === 'Sent' || ticket.status === 'Auto-Sent';
        const isSelected = selectedTicketId === ticket.id;

        return (
            <div
                key={ticket.id}
                className={`border-b border-zinc-800/50 transition-all duration-200 ${isSelected ? 'bg-zinc-800/50' : 'hover:bg-zinc-800/30'}`}
            >
                {/* Ticket Header */}
                <div
                    className="p-4 cursor-pointer"
                    onClick={() => handleSelectTicket(ticket.id)}
                >
                    <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                            <span className="text-sm font-mono text-zinc-500">{ticket.id}</span>
                            {ticket.status === 'Auto-Sent' && (
                                <Bot className="w-3.5 h-3.5 text-violet-400" />
                            )}
                            {ticket.status === 'Sent' && ticket.sentBy === 'human' && (
                                <User className="w-3.5 h-3.5 text-emerald-400" />
                            )}
                        </div>
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${getStatusBadge(ticket)}`}>
                            {ticket.status}
                        </span>
                    </div>
                    <p className="font-medium text-zinc-200 text-sm">{ticket.subject}</p>
                    <p className="text-xs text-zinc-500 mt-1">{ticket.customer}</p>

                    {/* Sentiment & Urgency */}
                    {(ticket.sentiment || ticket.urgency) && (
                        <div className="flex items-center gap-2 mt-2">
                            {ticket.sentiment && (
                                <span className="text-sm" title={ticket.sentiment}>
                                    {getSentimentEmoji(ticket.sentiment)}
                                </span>
                            )}
                            {ticket.urgency && ticket.urgency !== 'Medium' && (
                                <span className={`text-[9px] px-1.5 py-0.5 rounded font-medium ${getUrgencyBadge(ticket.urgency).style}`}>
                                    {getUrgencyBadge(ticket.urgency).label}
                                </span>
                            )}
                        </div>
                    )}

                    {/* Suggested Sources for Open tickets */}
                    {ticket.status === 'Open' && suggestedSources.has(ticket.id) && (
                        <div className="mt-3 bg-zinc-900/30 rounded-lg p-2.5 border border-zinc-800/50">
                            <div className="flex items-center gap-1.5 mb-2">
                                <Database className="w-3 h-3 text-blue-400/80" />
                                <span className="text-[9px] uppercase tracking-wider text-zinc-600">AI Suggested Sources</span>
                            </div>
                            <div className="space-y-1.5">
                                {suggestedSources.get(ticket.id)?.slice(0, 3).map((source, idx) => (
                                    <div key={idx} className="flex items-center justify-between gap-2">
                                        <div className="flex-1 min-w-0">
                                            <p className="text-[10px] text-zinc-400 truncate">
                                                {source.document.replace('.md', '')}
                                            </p>
                                        </div>
                                        <span className={`text-[9px] px-1.5 py-0.5 rounded font-medium shrink-0 ${
                                            source.relevance >= 0.8
                                                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                                : 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                                        }`}>
                                            {Math.round(source.relevance * 100)}%
                                        </span>
                                    </div>
                                ))}
                            </div>
                            {(suggestedSources.get(ticket.id)?.length || 0) > 3 && (
                                <p className="text-[9px] text-zinc-600 mt-1.5">
                                    +{(suggestedSources.get(ticket.id)?.length || 0) - 3} more sources
                                </p>
                            )}
                        </div>
                    )}

                    {/* Draft Preview or Generate Button */}
                    {!isSent && (
                        <div className="mt-3">
                            {isProcessing ? (
                                <div className="flex items-center gap-2 text-blue-400 text-xs">
                                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                    <span>Generating...</span>
                                </div>
                            ) : hasDraft ? (
                                <div className="space-y-2">
                                    {/* Draft Preview */}
                                    <div
                                        className="bg-zinc-900/50 rounded-lg p-3 text-xs text-zinc-400 cursor-pointer hover:bg-zinc-900 transition-colors border border-zinc-800"
                                        onClick={(e) => { e.stopPropagation(); openEditor(ticket.id); }}
                                    >
                                        <div className="flex items-start justify-between gap-2">
                                            <p className={`leading-relaxed ${isExpanded ? '' : 'line-clamp-2'}`}>
                                                {ticket.draft!.text}
                                            </p>
                                            <button
                                                onClick={(e) => toggleExpand(ticket.id, e)}
                                                className="shrink-0 p-1 hover:bg-zinc-800 rounded text-zinc-500"
                                            >
                                                {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                                            </button>
                                        </div>

                                        {/* Confidence indicator */}
                                        <div className={`mt-2 flex items-center gap-2 text-[10px] ${ticket.draft!.confidence >= 0.8 ? 'text-emerald-400' : 'text-amber-400'}`}>
                                            {ticket.draft!.confidence >= 0.8 ? (
                                                <CheckCircle className="w-3 h-3" />
                                            ) : (
                                                <AlertTriangle className="w-3 h-3" />
                                            )}
                                            <span>{Math.round(ticket.draft!.confidence * 100)}%</span>
                                            {ticket.draft!.confidence >= 0.9 && (
                                                <span className="text-violet-400 flex items-center gap-1">
                                                    <Sparkles className="w-3 h-3" /> auto
                                                </span>
                                            )}
                                        </div>

                                        {/* RAG Sources badges */}
                                        {ticket.draft!.ragSources && ticket.draft!.ragSources.length > 0 && (
                                            <div className="mt-2.5">
                                                <div className="flex items-center gap-1.5 mb-1.5">
                                                    <Database className="w-3 h-3 text-blue-400/80" />
                                                    <span className="text-[9px] uppercase tracking-wider text-zinc-600">Sources Used</span>
                                                </div>
                                                <div className="flex flex-wrap gap-1">
                                                    {ticket.draft!.ragSources.slice(0, 3).map((source, idx) => (
                                                        <span
                                                            key={idx}
                                                            className="text-[9px] px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20"
                                                        >
                                                            {source.document.replace('.md', '')}
                                                        </span>
                                                    ))}
                                                    {ticket.draft!.ragSources.length > 3 && (
                                                        <span className="text-[9px] px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-500 border border-zinc-700">
                                                            +{ticket.draft!.ragSources.length - 3}
                                                        </span>
                                                    )}
                                                </div>
                                            </div>
                                        )}
                                    </div>

                                    {/* Action buttons */}
                                    <div className="flex gap-2">
                                        <button
                                            onClick={(e) => { e.stopPropagation(); openEditor(ticket.id); }}
                                            className="flex-1 px-3 py-1.5 text-xs text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded-lg transition-colors flex items-center justify-center gap-1.5 border border-zinc-800"
                                        >
                                            <Edit3 className="w-3 h-3" /> Edit
                                        </button>
                                        <button
                                            onClick={(e) => sendDraft(ticket.id, e)}
                                            disabled={isSending}
                                            className="flex-1 px-3 py-1.5 text-xs bg-zinc-200 text-zinc-900 rounded-lg hover:bg-white transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50 font-medium"
                                        >
                                            {isSending ? (
                                                <Loader2 className="w-3 h-3 animate-spin" />
                                            ) : (
                                                <Send className="w-3 h-3" />
                                            )}
                                            {isSending ? 'Sending' : 'Send'}
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                <button
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        // Use suggested sources if available
                                        const sources = suggestedSources.get(ticket.id);
                                        const sourceDocuments = sources?.map(s => s.document) || [];
                                        generateDraft(ticket.id, sourceDocuments.length > 0 ? sourceDocuments : undefined);
                                    }}
                                    className="w-full px-3 py-2 text-xs bg-zinc-800 text-zinc-300 rounded-lg hover:bg-zinc-700 transition-colors flex items-center justify-center gap-2 border border-zinc-700"
                                >
                                    <Sparkles className="w-3.5 h-3.5" />
                                    Generate Draft
                                </button>
                            )}
                        </div>
                    )}

                    {/* Sent timestamp */}
                    {isSent && ticket.sentAt && (
                        <div className="mt-2 flex items-center gap-1.5 text-[10px] text-zinc-600">
                            <Clock className="w-3 h-3" />
                            <span>{ticket.sentAt.toLocaleTimeString()}</span>
                        </div>
                    )}
                </div>
            </div>
        );
    };

    // Count tickets by status
    const openCount = tickets.filter(t => t.status === 'Open').length;
    const draftCount = tickets.filter(t => t.status === 'Draft Ready').length;
    const sentCount = tickets.filter(t => t.status === 'Sent' || t.status === 'Auto-Sent').length;
    const autoSentCount = tickets.filter(t => t.status === 'Auto-Sent').length;

    return (
        <div className="flex h-screen bg-zinc-950 text-zinc-100">
            {/* Sidebar: Full Height */}
            <div className="w-[380px] bg-zinc-900/50 border-r border-zinc-800 flex flex-col">
                {/* Header */}
                <div className="p-5 border-b border-zinc-800">
                    <div className="flex items-center gap-2 mb-4">
                        <Inbox className="w-5 h-5 text-zinc-400" />
                        <h1 className="text-lg font-semibold text-zinc-100">Support Queue</h1>
                    </div>
                    <div className="flex gap-2 text-[10px]">
                        <span className="px-2 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">{openCount} open</span>
                        <span className="px-2 py-1 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">{draftCount} drafts</span>
                        <span className="px-2 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">{sentCount} sent</span>
                        {autoSentCount > 0 && (
                            <span className="px-2 py-1 rounded-full bg-violet-500/10 text-violet-400 border border-violet-500/20 flex items-center gap-1">
                                <Bot className="w-3 h-3" /> {autoSentCount}
                            </span>
                        )}
                    </div>
                </div>

                {/* Ticket list */}
                <div className="overflow-y-auto flex-1">
                    {tickets.map(ticket => renderTicketCard(ticket))}
                </div>
            </div>

            {/* Right Side: Analytics + Main Area */}
            <div className="flex-1 flex flex-col">
                {/* Analytics Dashboard */}
                <AnalyticsDashboard tickets={tickets} />

                {/* Main Area: Editor or Details */}
                <div className="flex-1 flex flex-col overflow-hidden">
                {editingTicketId ? (
                    // Edit Mode
                    (() => {
                        const ticket = tickets.find(t => t.id === editingTicketId);
                        if (!ticket) return null;
                        return (
                            <div className="flex-1 overflow-y-auto flex flex-col">
                                {/* Scrollable Header Section */}
                                <div className="p-6 border-b border-zinc-800">
                                    <div className="flex justify-between items-start">
                                        <div>
                                            <p className="text-xs text-zinc-500 font-mono mb-1">{ticket.id}</p>
                                            <h1 className="text-xl font-semibold text-zinc-100">{ticket.subject}</h1>
                                            <p className="text-sm text-zinc-500 mt-1">{ticket.customer}</p>
                                        </div>
                                        <button
                                            onClick={() => {
                                                setEditingTicketId(null);
                                                setSelectedTicketId(null);
                                            }}
                                            className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-500 hover:text-zinc-300 transition-colors"
                                        >
                                            <X className="w-5 h-5" />
                                        </button>
                                    </div>

                                    {/* Original query */}
                                    <div className="mt-5 bg-zinc-900/50 p-4 rounded-lg border border-zinc-800">
                                        <p className="text-[10px] uppercase tracking-wider text-zinc-600 mb-2">Customer Message</p>
                                        <p className="text-sm text-zinc-300 leading-relaxed">{ticket.query}</p>
                                    </div>

                                    {/* Confidence banner */}
                                    {ticket.draft && (
                                        <div className={`mt-4 p-3 rounded-lg flex items-center gap-2 text-sm ${ticket.draft.confidence >= 0.8 ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'}`}>
                                            {ticket.draft.confidence >= 0.8 ? <CheckCircle className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
                                            <span className="font-medium">
                                                {Math.round(ticket.draft.confidence * 100)}% confidence
                                                {ticket.draft.confidence < 0.8 && " — review recommended"}
                                            </span>
                                        </div>
                                    )}
                                </div>

                                {/* Editor Section */}
                                <div className="p-6 flex-1 flex flex-col min-h-0">
                                    <label className="text-[10px] uppercase tracking-wider text-zinc-600 mb-2">Response</label>
                                    <textarea
                                        className="flex-1 w-full p-4 rounded-lg bg-zinc-900/50 border border-zinc-800 text-zinc-200 text-sm leading-relaxed resize-none focus:outline-none focus:border-zinc-700 focus:ring-1 focus:ring-zinc-700 placeholder-zinc-600"
                                        value={editDraft}
                                        onChange={(e) => setEditDraft(e.target.value)}
                                    />

                                    <div className="mt-4 flex justify-end gap-3">
                                        <button
                                            onClick={saveEdit}
                                            className="px-4 py-2 text-sm bg-zinc-800 text-zinc-200 rounded-lg hover:bg-zinc-700 transition-colors border border-zinc-700"
                                        >
                                            Save
                                        </button>
                                        <button
                                            onClick={(e) => { saveEdit(); sendDraft(editingTicketId, e); }}
                                            className="px-5 py-2 text-sm bg-zinc-100 text-zinc-900 rounded-lg hover:bg-white transition-colors flex items-center gap-2 font-medium"
                                        >
                                            <Send className="w-4 h-4" /> Send
                                        </button>
                                    </div>
                                </div>
                            </div>
                        );
                    })()
                ) : selectedTicket ? (
                    // Detail View
                    <>
                        {/* Always visible toggle bar */}
                        <div className="p-4 border-b border-zinc-800 bg-zinc-900/30">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <button
                                        onClick={() => setIsDetailCollapsed(!isDetailCollapsed)}
                                        className="p-1 hover:bg-zinc-800 rounded text-zinc-500 hover:text-zinc-300 transition-colors"
                                    >
                                        {isDetailCollapsed ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
                                    </button>
                                    <p className="text-xs text-zinc-500 font-mono">{selectedTicket.id}</p>
                                    <p className="text-sm text-zinc-400">{selectedTicket.subject}</p>
                                    {selectedTicket.status === 'Auto-Sent' && (
                                        <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-violet-500/10 text-violet-400 border border-violet-500/20">
                                            <Bot className="w-3 h-3" /> Auto-sent
                                        </span>
                                    )}
                                </div>
                                <span className={`text-xs px-3 py-1 rounded-full font-medium ${getStatusBadge(selectedTicket)}`}>
                                    {selectedTicket.status}
                                </span>
                            </div>
                        </div>

                        {/* Expandable detail content */}
                        {!isDetailCollapsed && (
                            <div className="px-6 py-4 border-b border-zinc-800 bg-zinc-900/20">
                                <div className="mb-4">
                                    <p className="text-sm text-zinc-500 mb-3">{selectedTicket.customer}</p>

                                    {/* Sentiment & Urgency Tags */}
                                    {(selectedTicket.sentiment || selectedTicket.urgency) && (
                                        <div className="flex items-center gap-2">
                                            {selectedTicket.sentiment && (
                                                <span className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full bg-zinc-800 border border-zinc-700">
                                                    <span className="text-base">{getSentimentEmoji(selectedTicket.sentiment)}</span>
                                                    <span className="text-zinc-400">{selectedTicket.sentiment}</span>
                                                </span>
                                            )}
                                            {selectedTicket.urgency && (
                                                <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${getUrgencyBadge(selectedTicket.urgency).style}`}>
                                                    {getUrgencyBadge(selectedTicket.urgency).label} Urgency
                                                </span>
                                            )}
                                        </div>
                                    )}
                                </div>

                                <div className="bg-zinc-900/50 p-4 rounded-lg border border-zinc-800">
                                    <p className="text-[10px] uppercase tracking-wider text-zinc-600 mb-2">Customer Message</p>
                                    <p className="text-sm text-zinc-300 leading-relaxed">{selectedTicket.query}</p>
                                </div>
                            </div>
                        )}

                        {/* Response section */}
                        <div className="p-6 flex-1 overflow-y-auto">
                            {selectedTicket.draft ? (
                                <div>
                                    <div className="flex items-center justify-between mb-4">
                                        <h3 className="text-[10px] uppercase tracking-wider text-zinc-600">
                                            {selectedTicket.status === 'Sent' || selectedTicket.status === 'Auto-Sent'
                                                ? 'Sent Response'
                                                : 'AI Draft'}
                                        </h3>
                                        {selectedTicket.draft.confidence && (
                                            <span className={`flex items-center gap-1.5 text-xs ${selectedTicket.draft.confidence >= 0.8 ? 'text-emerald-400' : 'text-amber-400'}`}>
                                                {selectedTicket.draft.confidence >= 0.8 ? <CheckCircle className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
                                                {Math.round(selectedTicket.draft.confidence * 100)}%
                                            </span>
                                        )}
                                    </div>

                                    <div className="bg-zinc-900/30 border border-zinc-800 rounded-lg p-5 text-sm text-zinc-300 leading-relaxed whitespace-pre-wrap">
                                        {selectedTicket.draft.text}
                                    </div>

                                    {selectedTicket.draft.critique && (
                                        <p className="mt-4 text-xs text-zinc-600 italic">
                                            {selectedTicket.draft.critique}
                                        </p>
                                    )}

                                    {/* RAG Sources Panel */}
                                    {selectedTicket.draft.ragSources && selectedTicket.draft.ragSources.length > 0 && (
                                        <div className="mt-6">
                                            <div className="flex items-center gap-2 mb-3">
                                                <Database className="w-4 h-4 text-blue-400" />
                                                <h4 className="text-[10px] uppercase tracking-wider text-zinc-600">
                                                    Knowledge Base Sources
                                                </h4>
                                            </div>
                                            <div className="space-y-2">
                                                {selectedTicket.draft.ragSources.map((source, idx) => (
                                                    <div
                                                        key={idx}
                                                        className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-3 hover:border-blue-500/30 transition-colors"
                                                    >
                                                        <div className="flex items-start justify-between gap-2">
                                                            <div className="flex-1 min-w-0">
                                                                <div className="flex items-center gap-2 mb-1">
                                                                    <BookOpen className="w-3.5 h-3.5 text-blue-400 shrink-0" />
                                                                    <p className="text-xs font-medium text-zinc-300 truncate">
                                                                        {source.document.replace('.md', '')}
                                                                    </p>
                                                                </div>
                                                                <p className="text-[10px] text-zinc-500">
                                                                    {source.section}
                                                                </p>
                                                                {source.content_preview && (
                                                                    <p className="text-[10px] text-zinc-600 mt-2 line-clamp-2">
                                                                        {source.content_preview}
                                                                    </p>
                                                                )}
                                                            </div>
                                                            <div className="flex flex-col items-end gap-1 shrink-0">
                                                                <span className={`text-[10px] px-2 py-0.5 rounded-full ${
                                                                    source.relevance >= 0.8
                                                                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                                                        : 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                                                                }`}>
                                                                    {Math.round(source.relevance * 100)}%
                                                                </span>
                                                                <span className="text-[9px] text-zinc-600">
                                                                    {source.category}
                                                                </span>
                                                            </div>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                            <p className="mt-3 text-[10px] text-zinc-600 flex items-center gap-1.5">
                                                <Sparkles className="w-3 h-3" />
                                                This response was generated using {selectedTicket.draft.ragSources.length} relevant document{selectedTicket.draft.ragSources.length !== 1 ? 's' : ''} from our knowledge base
                                            </p>
                                        </div>
                                    )}

                                    {selectedTicket.sentAt && (
                                        <p className="mt-4 text-xs text-zinc-600 flex items-center gap-1.5">
                                            <Clock className="w-3.5 h-3.5" />
                                            Sent {selectedTicket.sentAt.toLocaleString()}
                                            {selectedTicket.sentBy === 'ai' && ' (auto)'}
                                        </p>
                                    )}

                                    {selectedTicket.status === 'Draft Ready' && (
                                        <>
                                            <div className="mt-6 flex gap-3">
                                                <button
                                                    onClick={() => setShowSourceSelector(prev => new Set(prev).add(selectedTicket.id))}
                                                    className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded-lg flex items-center gap-2 transition-colors border border-zinc-800"
                                                >
                                                    <Database className="w-4 h-4" /> Change Sources
                                                </button>
                                                <button
                                                    onClick={() => openEditor(selectedTicket.id)}
                                                    className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded-lg flex items-center gap-2 transition-colors border border-zinc-800"
                                                >
                                                    <Edit3 className="w-4 h-4" /> Edit
                                                </button>
                                                <button
                                                    onClick={(e) => sendDraft(selectedTicket.id, e)}
                                                    disabled={sendingTickets.has(selectedTicket.id)}
                                                    className="px-5 py-2 text-sm bg-zinc-100 text-zinc-900 rounded-lg hover:bg-white flex items-center gap-2 disabled:opacity-50 transition-colors font-medium"
                                                >
                                                    {sendingTickets.has(selectedTicket.id) ? (
                                                        <Loader2 className="w-4 h-4 animate-spin" />
                                                    ) : (
                                                        <Send className="w-4 h-4" />
                                                    )}
                                                    Send Reply
                                                </button>
                                            </div>

                                            {/* Source Selector for Regeneration */}
                                            {showSourceSelector.has(selectedTicket.id) && (
                                                <div className="mt-6">
                                                    <RAGSourceSelector
                                                        ticketQuery={selectedTicket.query}
                                                        aiSelectedSources={selectedTicket.draft.ragSources?.map(s => s.document) || []}
                                                        onRegenerateDraft={(sources) => generateDraft(selectedTicket.id, sources)}
                                                        isGenerating={processingTickets.has(selectedTicket.id)}
                                                    />
                                                </div>
                                            )}
                                        </>
                                    )}
                                </div>
                            ) : selectedTicket.status === 'Open' ? (
                                <div className="p-6">
                                    {!showSourceSelector.has(selectedTicket.id) ? (
                                        <div className="flex flex-col items-center justify-center h-full text-center py-12">
                                            <div className="w-16 h-16 rounded-full bg-zinc-900 flex items-center justify-center mb-4 border border-zinc-800">
                                                <Sparkles className="w-7 h-7 text-zinc-600" />
                                            </div>
                                            <p className="text-zinc-500 mb-2 text-sm">No draft generated</p>
                                            <p className="text-zinc-600 text-xs mb-5">Select knowledge sources and generate a response</p>
                                            <button
                                                onClick={() => setShowSourceSelector(prev => new Set(prev).add(selectedTicket.id))}
                                                className="px-5 py-2.5 text-sm bg-zinc-100 text-zinc-900 rounded-lg hover:bg-white flex items-center gap-2 transition-colors font-medium"
                                            >
                                                <Database className="w-4 h-4" />
                                                Select Sources & Generate
                                            </button>
                                        </div>
                                    ) : (
                                        <RAGSourceSelector
                                            ticketQuery={selectedTicket.query}
                                            aiSelectedSources={[]}
                                            onRegenerateDraft={(sources) => generateDraft(selectedTicket.id, sources)}
                                            isGenerating={processingTickets.has(selectedTicket.id)}
                                        />
                                    )}
                                </div>
                            ) : null}
                        </div>
                    </>
                ) : (
                    <div className="flex-1 flex flex-col items-center justify-center text-zinc-600">
                        <div className="w-20 h-20 rounded-full bg-zinc-900/50 flex items-center justify-center mb-5 border border-zinc-800">
                            <Mail className="w-8 h-8" />
                        </div>
                        <p className="text-sm">Select a ticket</p>
                        <p className="text-xs text-zinc-700 mt-1">or generate drafts from the sidebar</p>
                    </div>
                )}
                </div>
            </div>
        </div>
    );
}
