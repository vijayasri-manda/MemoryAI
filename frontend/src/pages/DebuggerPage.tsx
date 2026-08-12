/**
 * Prompt Debugger & Retrieval Explainability Page.
 * Visualizes the complete RAG pipeline: Query -> Embedding -> Summaries -> Memories -> Ranking -> Prompt -> Gemini.
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import {
  Terminal, Search, Cpu, Database, Layers, ArrowRight,
  Clock, Copy, Download, ChevronDown, ChevronUp, ChevronLeft,
  Check, RefreshCw, Zap, Shield, ToggleLeft, ToggleRight, Sparkles, FileText
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { debugApi } from '@/lib/api';
import { Spinner, EmptyState } from '@/components/ui/shared';
import { toast } from '@/components/ui/Toast';
import { cn } from '@/lib/utils';

export function DebuggerPage() {
  const [developerMode, setDeveloperMode] = useState(false);
  const [promptExpanded, setPromptExpanded] = useState(false);

  const { data: trace, isLoading, refetch } = useQuery({
    queryKey: ['debug-latest'],
    queryFn: debugApi.getLatest,
    refetchInterval: 10_000,
  });

  const copyPrompt = () => {
    if (trace?.final_prompt) {
      navigator.clipboard.writeText(trace.final_prompt);
      toast.success('Prompt copied to clipboard');
    }
  };

  const downloadPrompt = () => {
    if (!trace?.final_prompt) return;
    const blob = new Blob([trace.final_prompt], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `prompt_debug_${trace.id || 'trace'}.txt`;
    link.click();
    URL.revokeObjectURL(url);
    toast.success('Prompt downloaded');
  };

  return (
    <div className="min-h-screen bg-surface-950 text-surface-100 font-sans">
      {/* Top Header */}
      <header className="sticky top-0 z-20 bg-surface-950/90 backdrop-blur-lg border-b border-surface-700/50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/chat" className="btn-ghost gap-2">
              <ChevronLeft className="w-4 h-4" />Back to Chat
            </Link>
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-accent-blue flex items-center justify-center shadow-lg shadow-brand-500/20">
                <Terminal className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="font-bold text-surface-50 text-lg">Prompt Debugger</h1>
                <p className="text-xs text-surface-400">RAG pipeline explainability & telemetry inspection</p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Developer Mode Toggle */}
            <button
              onClick={() => setDeveloperMode(!developerMode)}
              className={cn(
                "flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs font-semibold transition-all",
                developerMode
                  ? "bg-brand-500/20 border-brand-500/50 text-brand-300 shadow-sm shadow-brand-500/10"
                  : "bg-surface-900 border-surface-700 text-surface-400 hover:text-surface-200"
              )}
            >
              {developerMode ? <ToggleRight className="w-4 h-4 text-brand-400" /> : <ToggleLeft className="w-4 h-4" />}
              <span>Developer Mode</span>
            </button>

            <button onClick={() => refetch()} className="btn-ghost text-xs gap-2">
              <RefreshCw className="w-4 h-4" /> Refresh
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {isLoading ? (
          <div className="flex justify-center py-24"><Spinner size="lg" /></div>
        ) : !trace ? (
          <EmptyState
            icon={<Terminal className="w-12 h-12 text-surface-500" />}
            title="No RAG Debug Traces Available"
            description="Send a message in the chat to record real-time RAG prompt construction & retrieval explainability."
            action={<Link to="/chat" className="btn-primary">Go to Chat</Link>}
          />
        ) : (
          <div className="space-y-8">

            {/* Execution Timeline Visualization */}
            <div className="glass rounded-2xl p-6 border-surface-700/60 shadow-xl">
              <h2 className="text-xs font-bold uppercase tracking-wider text-surface-400 mb-4 flex items-center gap-2">
                <Layers className="w-4 h-4 text-brand-400" /> Execution Pipeline Visualizer
              </h2>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-9 gap-2 items-center text-center">
                <TimelineStep title="User Query" subtitle="Trigger" color="emerald" />
                <ArrowRight className="hidden lg:block w-4 h-4 text-surface-600 mx-auto" />
                <TimelineStep title="Embedding" subtitle={`${trace.embedding_time_ms ?? 12}ms`} color="brand" />
                <ArrowRight className="hidden lg:block w-4 h-4 text-surface-600 mx-auto" />
                <TimelineStep title="Summaries" subtitle={`${trace.total_summaries ?? 0} items`} color="blue" />
                <ArrowRight className="hidden lg:block w-4 h-4 text-surface-600 mx-auto" />
                <TimelineStep title="Memories" subtitle={`${trace.total_memories ?? 0} items`} color="purple" />
                <ArrowRight className="hidden lg:block w-4 h-4 text-surface-600 mx-auto" />
                <TimelineStep title="Gemini LLM" subtitle={`${trace.response_time_ms ?? 0}ms`} color="pink" />
              </div>
            </div>

            {/* Developer Mode Metrics Banner */}
            {developerMode && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 p-4 rounded-2xl bg-brand-950/40 border border-brand-500/30 text-xs"
              >
                <div>
                  <span className="text-surface-400 block">Embedding Model</span>
                  <span className="font-mono text-brand-300 font-semibold">{trace.embedding_model}</span>
                </div>
                <div>
                  <span className="text-surface-400 block">Vector Dimensions</span>
                  <span className="font-mono text-brand-300 font-semibold">{trace.embedding_dimension ?? 768} dim</span>
                </div>
                <div>
                  <span className="text-surface-400 block">Embedding Latency</span>
                  <span className="font-mono text-brand-300 font-semibold">{trace.embedding_time_ms} ms</span>
                </div>
                <div>
                  <span className="text-surface-400 block">Summary Retrieval</span>
                  <span className="font-mono text-brand-300 font-semibold">{trace.summary_retrieval_time_ms} ms</span>
                </div>
                <div>
                  <span className="text-surface-400 block">Memory Retrieval</span>
                  <span className="font-mono text-brand-300 font-semibold">{trace.memory_retrieval_time_ms} ms</span>
                </div>
                <div>
                  <span className="text-surface-400 block">Prompt Length</span>
                  <span className="font-mono text-brand-300 font-semibold">{trace.prompt_token_length} words</span>
                </div>
              </motion.div>
            )}

            {/* Section 1: Original User Query */}
            <div className="glass rounded-2xl p-6 border-surface-700/60 space-y-3">
              <div className="flex items-center justify-between border-b border-surface-700/50 pb-3">
                <h3 className="text-sm font-bold text-surface-50 flex items-center gap-2">
                  <Search className="w-4 h-4 text-emerald-400" /> Section 1: Original User Query
                </h3>
                <span className="text-xs font-mono text-surface-400">{trace.timestamp}</span>
              </div>
              <div className="p-4 rounded-xl bg-surface-900/90 border border-surface-700/40 text-surface-100 font-medium text-sm">
                "{trace.query}"
              </div>
            </div>

            {/* Section 2: Retrieved Conversation Summaries */}
            <div className="glass rounded-2xl p-6 border-surface-700/60 space-y-4">
              <div className="flex items-center justify-between border-b border-surface-700/50 pb-3">
                <h3 className="text-sm font-bold text-surface-50 flex items-center gap-2">
                  <FileText className="w-4 h-4 text-accent-blue" /> Section 2: Retrieved Conversation Summaries ({trace.retrieved_summaries?.length ?? 0})
                </h3>
              </div>

              {!trace.retrieved_summaries || trace.retrieved_summaries.length === 0 ? (
                <p className="text-xs text-surface-400 italic">No conversation summaries matched threshold for this query.</p>
              ) : (
                <div className="grid grid-cols-1 gap-3">
                  {trace.retrieved_summaries.map((sum: any, i: number) => (
                    <div key={i} className="p-4 rounded-xl bg-surface-900/60 border border-surface-700/40 space-y-2">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-semibold text-accent-blue">Summary #{i + 1}</span>
                        <span className="font-mono text-surface-300">Similarity Score: {(sum.similarity_score * 100).toFixed(1)}%</span>
                      </div>
                      <p className="text-xs text-surface-200 leading-relaxed font-mono whitespace-pre-wrap">{sum.summary}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Section 3: Retrieved Memories */}
            <div className="glass rounded-2xl p-6 border-surface-700/60 space-y-4">
              <div className="flex items-center justify-between border-b border-surface-700/50 pb-3">
                <h3 className="text-sm font-bold text-surface-50 flex items-center gap-2">
                  <Database className="w-4 h-4 text-accent-purple" /> Section 3: Retrieved Detailed Memories ({trace.retrieved_memories?.length ?? 0})
                </h3>
              </div>

              {!trace.retrieved_memories || trace.retrieved_memories.length === 0 ? (
                <p className="text-xs text-surface-400 italic">No granular memories retrieved above similarity threshold.</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {trace.retrieved_memories.map((mem: any) => (
                    <div key={mem.id} className="p-4 rounded-xl bg-surface-900/60 border border-surface-700/40 space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold px-2 py-0.5 rounded bg-brand-500/20 text-brand-300 capitalize border border-brand-500/30">
                          {mem.category}
                        </span>
                        <span className="text-[11px] font-mono text-emerald-400">Similarity: {(mem.similarity_score * 100).toFixed(1)}%</span>
                      </div>
                      <p className="text-xs text-surface-100 font-medium leading-relaxed">{mem.memory}</p>
                      <div className="text-[11px] text-surface-400 space-y-1 pt-2 border-t border-surface-800">
                        <p><span className="text-surface-500">Retrieval Reason:</span> {mem.reason}</p>
                        <p><span className="text-surface-500">Importance Score:</span> {(mem.importance_score * 100).toFixed(0)}% | <span className="text-surface-500">Status:</span> {mem.status} (v{mem.version})</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Section 4: Ranking Breakdown Table */}
            {trace.ranking_breakdown && trace.ranking_breakdown.length > 0 && (
              <div className="glass rounded-2xl p-6 border-surface-700/60 space-y-3">
                <h3 className="text-sm font-bold text-surface-50 flex items-center gap-2 border-b border-surface-700/50 pb-3">
                  <Layers className="w-4 h-4 text-amber-400" /> Section 4: Memory Ranking Breakdown
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-surface-700/60 text-surface-400">
                        <th className="py-2.5 px-3">Rank</th>
                        <th className="py-2.5 px-3">Category</th>
                        <th className="py-2.5 px-3">Content Snippet</th>
                        <th className="py-2.5 px-3">Similarity (60%)</th>
                        <th className="py-2.5 px-3">Importance (40%)</th>
                        <th className="py-2.5 px-3 font-semibold text-brand-300">Final Composite Score</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-surface-800/50 text-surface-200">
                      {trace.ranking_breakdown.map((row: any) => (
                        <tr key={row.rank} className="hover:bg-surface-800/30 transition-colors">
                          <td className="py-2.5 px-3 font-mono font-bold text-surface-400">#{row.rank}</td>
                          <td className="py-2.5 px-3 capitalize"><span className="px-2 py-0.5 rounded bg-surface-800 text-surface-300 border border-surface-700">{row.category}</span></td>
                          <td className="py-2.5 px-3 font-mono text-surface-300">{row.content}</td>
                          <td className="py-2.5 px-3 font-mono">{(row.similarity_score * 100).toFixed(1)}%</td>
                          <td className="py-2.5 px-3 font-mono">{(row.importance_score * 100).toFixed(0)}%</td>
                          <td className="py-2.5 px-3 font-mono font-bold text-brand-300">{(row.final_score * 100).toFixed(1)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Section 5: Final Constructed Prompt */}
            <div className="glass rounded-2xl p-6 border-surface-700/60 space-y-4">
              <div className="flex items-center justify-between border-b border-surface-700/50 pb-3">
                <h3 className="text-sm font-bold text-surface-50 flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-brand-400" /> Section 5: Final Prompt Sent to Gemini
                </h3>
                <div className="flex items-center gap-2">
                  <button onClick={copyPrompt} className="btn-ghost text-xs gap-1.5">
                    <Copy className="w-3.5 h-3.5" /> Copy Prompt
                  </button>
                  <button onClick={downloadPrompt} className="btn-ghost text-xs gap-1.5">
                    <Download className="w-3.5 h-3.5" /> Download
                  </button>
                  <button onClick={() => setPromptExpanded(!promptExpanded)} className="btn-ghost text-xs gap-1">
                    {promptExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div className={cn("p-4 rounded-xl bg-surface-950 font-mono text-xs text-surface-300 overflow-x-auto whitespace-pre-wrap border border-surface-800 transition-all", promptExpanded ? "max-h-none" : "max-h-72 overflow-y-auto")}>
                {trace.final_prompt}
              </div>
            </div>

            {/* Section 6: Gemini Response Metadata */}
            <div className="glass rounded-2xl p-6 border-surface-700/60 space-y-4">
              <div className="flex items-center justify-between border-b border-surface-700/50 pb-3">
                <h3 className="text-sm font-bold text-surface-50 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-accent-pink" /> Section 6: Gemini Response
                </h3>
                <div className="flex items-center gap-3 text-xs font-mono text-surface-400">
                  <span>Model: <strong className="text-brand-300">{trace.model_name ?? 'gemini-2.5-flash'}</strong></span>
                  <span>Latency: <strong className="text-emerald-400">{trace.response_time_ms ?? 0} ms</strong></span>
                  <span>Tokens: <strong className="text-amber-300">{trace.token_usage?.total_tokens ?? 0}</strong></span>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-surface-900/80 border border-surface-700/40 text-surface-100 font-sans text-sm leading-relaxed whitespace-pre-wrap">
                {trace.gemini_response || 'No Gemini response captured.'}
              </div>
            </div>

          </div>
        )}
      </div>
    </div>
  );
}

function TimelineStep({ title, subtitle, color }: { title: string; subtitle: string; color: string }) {
  return (
    <div className="p-3 rounded-xl bg-surface-900/80 border border-surface-700/50 flex flex-col items-center">
      <span className="text-xs font-bold text-surface-100">{title}</span>
      <span className="text-[10px] font-mono text-surface-400 mt-0.5">{subtitle}</span>
    </div>
  );
}
