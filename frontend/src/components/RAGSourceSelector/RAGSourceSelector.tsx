import { useState, useEffect } from 'react';
import { Database, CheckCircle2, Circle, RefreshCw, Sparkles, BookOpen } from 'lucide-react';

interface RAGSource {
    id: string;
    document: string;
    category: string;
    sections: string[];
    total_chunks: number;
}

interface RAGSourceSelectorProps {
    ticketQuery: string;
    aiSelectedSources?: string[]; // Documents selected by AI
    onRegenerateDraft: (selectedDocuments: string[]) => void;
    isGenerating?: boolean;
}

export function RAGSourceSelector({
    ticketQuery,
    aiSelectedSources = [],
    onRegenerateDraft,
    isGenerating = false
}: RAGSourceSelectorProps) {
    const [availableSources, setAvailableSources] = useState<RAGSource[]>([]);
    const [selectedDocuments, setSelectedDocuments] = useState<Set<string>>(new Set(aiSelectedSources));
    const [loading, setLoading] = useState(true);

    // Fetch available sources
    useEffect(() => {
        fetchSources();
    }, []);

    // Update selected documents when AI selection changes
    useEffect(() => {
        setSelectedDocuments(new Set(aiSelectedSources));
    }, [aiSelectedSources]);

    const fetchSources = async () => {
        try {
            const response = await fetch('/api/sources');
            const data = await response.json();
            setAvailableSources(data.sources || []);
        } catch (error) {
            console.error('Error fetching sources:', error);
        } finally {
            setLoading(false);
        }
    };

    const toggleSource = (document: string) => {
        const newSelected = new Set(selectedDocuments);
        if (newSelected.has(document)) {
            newSelected.delete(document);
        } else {
            newSelected.add(document);
        }
        setSelectedDocuments(newSelected);
    };

    const handleRegenerate = () => {
        onRegenerateDraft(Array.from(selectedDocuments));
    };

    const getCategoryColor = (category: string) => {
        switch (category) {
            case 'Billing & Payments':
                return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';
            case 'Technical Support':
                return 'text-blue-400 bg-blue-500/10 border-blue-500/30';
            case 'Features & Usage':
                return 'text-violet-400 bg-violet-500/10 border-violet-500/30';
            default:
                return 'text-zinc-400 bg-zinc-500/10 border-zinc-500/30';
        }
    };

    if (loading) {
        return (
            <div className="bg-zinc-900/50 rounded-lg p-6 border border-zinc-800">
                <div className="flex items-center gap-2 text-zinc-500">
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span className="text-sm">Loading knowledge base sources...</span>
                </div>
            </div>
        );
    }

    return (
        <div className="bg-zinc-900/50 rounded-lg border border-zinc-800">
            {/* Header */}
            <div className="p-4 border-b border-zinc-800">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Database className="w-4 h-4 text-blue-400" />
                        <h3 className="text-sm font-medium text-zinc-200">RAG Knowledge Sources</h3>
                    </div>
                    <span className="text-xs text-zinc-500">
                        {selectedDocuments.size}/{availableSources.length} selected
                    </span>
                </div>
                <p className="text-xs text-zinc-600 mt-2">
                    Select which knowledge base documents to use for generating the response
                </p>
            </div>

            {/* Sources List */}
            <div className="p-4 space-y-2 max-h-[400px] overflow-y-auto">
                {availableSources.map((source) => {
                    const isSelected = selectedDocuments.has(source.document);
                    const wasAISelected = aiSelectedSources.includes(source.document);

                    return (
                        <div
                            key={source.id}
                            onClick={() => toggleSource(source.document)}
                            className={`p-3 rounded-lg border cursor-pointer transition-all ${
                                isSelected
                                    ? 'bg-blue-500/10 border-blue-500/50 hover:bg-blue-500/20'
                                    : 'bg-zinc-900/50 border-zinc-800 hover:border-zinc-700 hover:bg-zinc-900'
                            }`}
                        >
                            <div className="flex items-start gap-3">
                                {/* Checkbox */}
                                <div className="mt-0.5">
                                    {isSelected ? (
                                        <CheckCircle2 className="w-4 h-4 text-blue-400" />
                                    ) : (
                                        <Circle className="w-4 h-4 text-zinc-600" />
                                    )}
                                </div>

                                {/* Content */}
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 mb-1">
                                        <BookOpen className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                                        <p className="text-sm font-medium text-zinc-200 truncate">
                                            {source.document.replace('.md', '')}
                                        </p>
                                        {wasAISelected && (
                                            <span className="flex items-center gap-1 text-[9px] px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-400 border border-violet-500/30 shrink-0">
                                                <Sparkles className="w-2.5 h-2.5" />
                                                AI Pick
                                            </span>
                                        )}
                                    </div>
                                    <div className="flex items-center gap-2 mt-1">
                                        <span className={`text-[10px] px-2 py-0.5 rounded-full border ${getCategoryColor(source.category)}`}>
                                            {source.category}
                                        </span>
                                        <span className="text-[10px] text-zinc-600">
                                            {source.total_chunks} chunks • {source.sections.length} sections
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-zinc-800 flex items-center justify-between">
                <div className="text-[10px] text-zinc-600">
                    {selectedDocuments.size === 0 && (
                        <span className="text-amber-400">⚠️ Select at least one source</span>
                    )}
                </div>
                <button
                    onClick={handleRegenerate}
                    disabled={selectedDocuments.size === 0 || isGenerating}
                    className="px-4 py-2 text-xs bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                >
                    {isGenerating ? (
                        <>
                            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                            Generating...
                        </>
                    ) : (
                        <>
                            <Sparkles className="w-3.5 h-3.5" />
                            Generate Draft
                        </>
                    )}
                </button>
            </div>
        </div>
    );
}
