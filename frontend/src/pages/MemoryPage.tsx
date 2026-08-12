/**
 * Memory Dashboard — Full memory management page.
 * Provides transparency & control: inspect, search, filter, edit, archive, restore, copy, and delete memories.
 */
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Brain, Search, Trash2, Tag, Star, TrendingUp,
  RefreshCw, ChevronLeft, Edit3, Eye, Archive, RotateCcw,
  Copy, Clock, Check, Layers, AlertCircle, FileText, X
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { memoryApi } from '@/lib/api';
import { Badge, Progress, EmptyState, Spinner, Tooltip } from '@/components/ui/shared';
import { toast } from '@/components/ui/Toast';
import { formatDate, importanceLabel, cn } from '@/lib/utils';
import type { Memory, MemoryStats } from '@/types';

const CATEGORIES = [
  { id: 'all', label: 'All' },
  { id: 'preference', label: 'Preference' },
  { id: 'project', label: 'Project' },
  { id: 'goal', label: 'Goal' },
  { id: 'coding', label: 'Coding' },
  { id: 'learning', label: 'Learning' },
  { id: 'personal', label: 'Personal' },
  { id: 'temporary', label: 'Temporary' },
  { id: 'general', label: 'General' },
];

export function MemoryPage() {
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'archived'>('all');
  const [page, setPage] = useState(1);
  const [editingMemory, setEditingMemory] = useState<Memory | null>(null);
  const [detailMemory, setDetailMemory] = useState<Memory | null>(null);

  const qc = useQueryClient();

  const { data: stats, refetch: refetchStats } = useQuery({
    queryKey: ['memory-stats'],
    queryFn: memoryApi.stats,
  });

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['memories', page, categoryFilter, statusFilter, search],
    queryFn: () => memoryApi.list({
      page,
      page_size: 20,
      memory_type: categoryFilter === 'all' ? undefined : categoryFilter,
      is_active: statusFilter === 'active' ? true : statusFilter === 'archived' ? false : undefined,
      search_query: search.length > 0 ? search : undefined,
    }),
  });

  // Mutations
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Memory> }) => memoryApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['memories'] });
      qc.invalidateQueries({ queryKey: ['memory-stats'] });
      toast.success('Memory updated successfully');
      setEditingMemory(null);
    },
    onError: () => toast.error('Failed to update memory'),
  });

  const archiveMutation = useMutation({
    mutationFn: (id: string) => memoryApi.archive(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['memories'] });
      qc.invalidateQueries({ queryKey: ['memory-stats'] });
      toast.success('Memory archived');
    },
    onError: () => toast.error('Failed to archive memory'),
  });

  const restoreMutation = useMutation({
    mutationFn: (id: string) => memoryApi.restore(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['memories'] });
      qc.invalidateQueries({ queryKey: ['memory-stats'] });
      toast.success('Memory restored to active');
    },
    onError: () => toast.error('Failed to restore memory'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => memoryApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['memories'] });
      qc.invalidateQueries({ queryKey: ['memory-stats'] });
      toast.success('Memory permanently deleted');
    },
    onError: () => toast.error('Failed to delete memory'),
  });

  const memories: Memory[] = data?.items ?? [];
  const total = data?.total ?? 0;
  const page_size = data?.page_size ?? 20;
  const pages = Math.ceil(total / page_size) || 1;

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  return (
    <div className="min-h-screen bg-surface-950 text-surface-100">
      {/* Top Header */}
      <header className="sticky top-0 z-20 bg-surface-950/90 backdrop-blur-lg border-b border-surface-700/50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/chat" className="btn-ghost gap-2">
              <ChevronLeft className="w-4 h-4" />Back to Chat
            </Link>
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-accent-purple flex items-center justify-center shadow-lg shadow-brand-500/20">
                <Brain className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="font-bold text-surface-50 text-lg">Memory Dashboard</h1>
                <p className="text-xs text-surface-400">Inspect, edit, and organize AI long-term memories</p>
              </div>
            </div>
          </div>
          <button onClick={() => { refetch(); refetchStats(); }} className="btn-ghost text-xs gap-2">
            <RefreshCw className="w-4 h-4" /> Refresh
          </button>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Top Section Statistics */}
        {stats && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
            <StatsCard icon={<Brain className="w-5 h-5 text-brand-400" />} label="Total Memories" value={stats.total_memories} />
            <StatsCard icon={<Star className="w-5 h-5 text-emerald-400" />} label="Active Memories" value={stats.active_memories} />
            <StatsCard icon={<RefreshCw className="w-5 h-5 text-amber-400" />} label="Updated Memories" value={stats.updated_memories ?? 0} />
            <StatsCard icon={<FileText className="w-5 h-5 text-accent-blue" />} label="Summaries" value={stats.summaries_count ?? 0} />
            <StatsCard icon={<TrendingUp className="w-5 h-5 text-accent-pink" />} label="Avg Importance" value={`${(stats.avg_importance * 100).toFixed(0)}%`} />
            <StatsCard icon={<Clock className="w-5 h-5 text-surface-400" />} label="Last Updated" value={stats.last_updated ? formatDate(stats.last_updated) : 'N/A'} isText />
          </div>
        )}

        {/* Search & Main Filter Controls */}
        <div className="flex flex-col md:flex-row gap-4 mb-6 items-center justify-between">
          <div className="relative flex-1 w-full">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-500" />
            <input
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              placeholder="Search memories by content, category, or tags..."
              className="input pl-11 w-full bg-surface-900 border-surface-700/60 focus:border-brand-500/50 text-sm"
            />
          </div>

          <div className="flex items-center gap-2 w-full md:w-auto">
            <span className="text-xs text-surface-400">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value as any); setPage(1); }}
              className="input bg-surface-900 border-surface-700/60 text-xs py-2 px-3"
            >
              <option value="all">All Memories</option>
              <option value="active">Active Only</option>
              <option value="archived">Archived Only</option>
            </select>
          </div>
        </div>

        {/* Category Filters */}
        <div className="flex flex-wrap gap-2 mb-8 border-b border-surface-700/50 pb-4">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.id}
              onClick={() => { setCategoryFilter(cat.id); setPage(1); }}
              className={cn(
                'px-3.5 py-1.5 rounded-xl text-xs font-medium transition-all duration-150 border',
                categoryFilter === cat.id
                  ? 'bg-brand-500/20 text-brand-300 border-brand-500/40 shadow-sm'
                  : 'bg-surface-900/60 text-surface-400 border-surface-700/40 hover:bg-surface-800 hover:text-surface-200'
              )}
            >
              {cat.label}
              {stats?.by_type && stats.by_type[cat.id] !== undefined && (
                <span className="ml-1.5 text-[10px] opacity-70">({stats.by_type[cat.id]})</span>
              )}
            </button>
          ))}
        </div>

        {/* Memory Grid */}
        {isLoading ? (
          <div className="flex justify-center py-20"><Spinner size="lg" /></div>
        ) : memories.length === 0 ? (
          <EmptyState
            icon={<Brain className="w-12 h-12 text-surface-500" />}
            title="No memories found"
            description="Try adjusting your search terms or filters."
            action={
              <button onClick={() => { setSearch(''); setCategoryFilter('all'); setStatusFilter('all'); }} className="btn-ghost text-xs">
                Reset Filters
              </button>
            }
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {memories.map((memory, idx) => (
              <motion.div
                key={memory.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.02 }}
                className={cn(
                  'card glass relative flex flex-col justify-between p-5 transition-all duration-200 border-surface-700/60 hover:border-brand-500/40 hover:shadow-xl',
                  !memory.is_active && 'opacity-60 bg-surface-950/40'
                )}
              >
                <div>
                  {/* Top Bar: Category & Status */}
                  <div className="flex items-center justify-between mb-3">
                    <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-lg bg-brand-500/10 text-brand-300 border border-brand-500/20 capitalize">
                      <Tag className="w-3 h-3 text-brand-400" />
                      {memory.memory_type || 'General'}
                    </span>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-800 text-surface-400 border border-surface-700">
                        v{memory.version ?? 1}
                      </span>
                      <span className={cn(
                        'text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider',
                        memory.status === 'UPDATED' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' :
                        memory.status === 'ARCHIVED' || !memory.is_active ? 'bg-surface-700 text-surface-400' :
                        'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                      )}>
                        {memory.status ?? (memory.is_active ? 'ACTIVE' : 'ARCHIVED')}
                      </span>
                    </div>
                  </div>

                  {/* Content */}
                  <p className="text-sm text-surface-100 font-normal leading-relaxed mb-4 line-clamp-4">
                    {memory.content}
                  </p>

                  {/* Importance & Confidence */}
                  <div className="space-y-2 mb-4">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-surface-400">Importance</span>
                      <span className="font-medium text-surface-200">
                        {(memory.importance_score * 100).toFixed(0)}% ({importanceLabel(memory.importance_score)})
                      </span>
                    </div>
                    <Progress
                      value={memory.importance_score}
                      colorClass={memory.importance_score >= 0.8 ? 'bg-emerald-400' : memory.importance_score >= 0.5 ? 'bg-brand-400' : 'bg-surface-500'}
                    />
                  </div>

                  {/* Tags */}
                  {memory.tags && memory.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-4">
                      {memory.tags.slice(0, 4).map((tag) => (
                        <Badge key={tag} variant="brand" className="text-[10px] px-2 py-0.5">
                          {tag}
                        </Badge>
                      ))}
                      {memory.tags.length > 4 && (
                        <span className="text-[10px] text-surface-400 self-center">+{memory.tags.length - 4}</span>
                      )}
                    </div>
                  )}
                </div>

                {/* Footer Actions & Dates */}
                <div className="pt-3 border-t border-surface-700/50 flex items-center justify-between">
                  <span className="text-[11px] text-surface-400 flex items-center gap-1">
                    <Clock className="w-3 h-3 text-surface-500" />
                    {formatDate(memory.created_at)}
                  </span>

                  <div className="flex items-center gap-1">
                    <Tooltip tip="View Details">
                      <button onClick={() => setDetailMemory(memory)} className="btn-icon p-1.5 hover:text-brand-300">
                        <Eye className="w-3.5 h-3.5" />
                      </button>
                    </Tooltip>
                    <Tooltip tip="Edit Memory">
                      <button onClick={() => setEditingMemory(memory)} className="btn-icon p-1.5 hover:text-brand-300">
                        <Edit3 className="w-3.5 h-3.5" />
                      </button>
                    </Tooltip>
                    <Tooltip tip="Copy Text">
                      <button onClick={() => copyToClipboard(memory.content)} className="btn-icon p-1.5 hover:text-brand-300">
                        <Copy className="w-3.5 h-3.5" />
                      </button>
                    </Tooltip>
                    {memory.is_active ? (
                      <Tooltip tip="Archive">
                        <button onClick={() => archiveMutation.mutate(memory.id)} className="btn-icon p-1.5 text-amber-400 hover:text-amber-300">
                          <Archive className="w-3.5 h-3.5" />
                        </button>
                      </Tooltip>
                    ) : (
                      <Tooltip tip="Restore">
                        <button onClick={() => restoreMutation.mutate(memory.id)} className="btn-icon p-1.5 text-emerald-400 hover:text-emerald-300">
                          <RotateCcw className="w-3.5 h-3.5" />
                        </button>
                      </Tooltip>
                    )}
                    <Tooltip tip="Delete">
                      <button onClick={() => deleteMutation.mutate(memory.id)} className="btn-icon p-1.5 text-surface-500 hover:text-red-400">
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </Tooltip>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}

        {/* Pagination */}
        {pages > 1 && (
          <div className="flex items-center justify-center gap-3 mt-10">
            <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1} className="btn-ghost text-xs px-4 py-2 border border-surface-700">
              ← Previous
            </button>
            <span className="text-xs text-surface-400 font-medium">Page {page} of {pages}</span>
            <button onClick={() => setPage((p) => Math.min(pages, p + 1))} disabled={page === pages} className="btn-ghost text-xs px-4 py-2 border border-surface-700">
              Next →
            </button>
          </div>
        )}
      </div>

      {/* Edit Modal */}
      <AnimatePresence>
        {editingMemory && (
          <EditMemoryModal
            memory={editingMemory}
            onClose={() => setEditingMemory(null)}
            onSave={(data) => updateMutation.mutate({ id: editingMemory.id, data })}
            isPending={updateMutation.isPending}
          />
        )}
      </AnimatePresence>

      {/* Detail Modal */}
      <AnimatePresence>
        {detailMemory && (
          <MemoryDetailModal
            memory={detailMemory}
            onClose={() => setDetailMemory(null)}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

function StatsCard({ icon, label, value, isText }: { icon: React.ReactNode; label: string; value: string | number; isText?: boolean }) {
  return (
    <div className="glass rounded-2xl p-4 border-surface-700/50">
      <div className="flex items-center gap-2 mb-1.5">{icon}<span className="text-xs text-surface-400 font-medium">{label}</span></div>
      <p className={cn("font-bold text-surface-50", isText ? "text-sm truncate" : "text-xl")}>{value}</p>
    </div>
  );
}

function EditMemoryModal({ memory, onClose, onSave, isPending }: {
  memory: Memory;
  onClose: () => void;
  onSave: (data: Partial<Memory>) => void;
  isPending: boolean;
}) {
  const [content, setContent] = useState(memory.content);
  const [memoryType, setMemoryType] = useState(memory.memory_type || 'general');
  const [importance, setImportance] = useState(memory.importance_score);

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="glass rounded-2xl max-w-lg w-full p-6 space-y-5 border-surface-700"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-surface-700/50 pb-3">
          <h3 className="text-base font-bold text-surface-50 flex items-center gap-2">
            <Edit3 className="w-4 h-4 text-brand-400" /> Edit Memory (v{memory.version ?? 1})
          </h3>
          <button onClick={onClose} className="btn-icon p-1"><X className="w-4 h-4" /></button>
        </div>

        <div className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs text-surface-300 font-medium">Memory Content</label>
            <textarea
              rows={4}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              className="input w-full bg-surface-900 border-surface-700 text-sm"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs text-surface-300 font-medium">Category</label>
            <select
              value={memoryType}
              onChange={(e) => setMemoryType(e.target.value)}
              className="input w-full bg-surface-900 border-surface-700 text-sm capitalize"
            >
              {CATEGORIES.filter(c => c.id !== 'all').map(c => (
                <option key={c.id} value={c.id}>{c.label}</option>
              ))}
            </select>
          </div>

          <div className="space-y-1.5">
            <div className="flex justify-between text-xs text-surface-300 font-medium">
              <span>Importance Score</span>
              <span>{(importance * 100).toFixed(0)}%</span>
            </div>
            <input
              type="range" min="0" max="1" step="0.05"
              value={importance}
              onChange={(e) => setImportance(parseFloat(e.target.value))}
              className="w-full accent-brand-500"
            />
          </div>
        </div>

        <div className="flex gap-3 justify-end pt-3 border-t border-surface-700/50">
          <button onClick={onClose} className="btn-ghost text-xs">Cancel</button>
          <button
            onClick={() => onSave({ content, memory_type: memoryType, importance_score: importance })}
            disabled={isPending}
            className="btn-primary text-xs px-5 py-2"
          >
            {isPending ? <Spinner size="sm" /> : 'Save Changes'}
          </button>
        </div>
      </motion.div>
    </div>
  );
}

function MemoryDetailModal({ memory, onClose }: { memory: Memory; onClose: () => void }) {
  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="glass rounded-2xl max-w-xl w-full p-6 space-y-5 border-surface-700"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-surface-700/50 pb-3">
          <h3 className="text-base font-bold text-surface-50 flex items-center gap-2">
            <Eye className="w-4 h-4 text-brand-400" /> Memory Details
          </h3>
          <button onClick={onClose} className="btn-icon p-1"><X className="w-4 h-4" /></button>
        </div>

        <div className="space-y-4 text-xs">
          <div>
            <span className="text-surface-400 block mb-1">Content:</span>
            <p className="p-3 rounded-xl bg-surface-900/80 border border-surface-700/50 text-surface-100 text-sm leading-relaxed">
              {memory.content}
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 rounded-xl bg-surface-900/50 border border-surface-700/30">
              <span className="text-surface-400 block mb-1">Category:</span>
              <span className="font-semibold text-brand-300 capitalize">{memory.memory_type || 'General'}</span>
            </div>
            <div className="p-3 rounded-xl bg-surface-900/50 border border-surface-700/30">
              <span className="text-surface-400 block mb-1">Status:</span>
              <span className="font-semibold text-emerald-300">{memory.status || (memory.is_active ? 'ACTIVE' : 'ARCHIVED')}</span>
            </div>
            <div className="p-3 rounded-xl bg-surface-900/50 border border-surface-700/30">
              <span className="text-surface-400 block mb-1">Importance:</span>
              <span className="font-semibold text-surface-100">{(memory.importance_score * 100).toFixed(0)}%</span>
            </div>
            <div className="p-3 rounded-xl bg-surface-900/50 border border-surface-700/30">
              <span className="text-surface-400 block mb-1">Version:</span>
              <span className="font-semibold text-surface-100">v{memory.version ?? 1}</span>
            </div>
            <div className="p-3 rounded-xl bg-surface-900/50 border border-surface-700/30">
              <span className="text-surface-400 block mb-1">Created At:</span>
              <span className="font-mono text-surface-300">{formatDate(memory.created_at)}</span>
            </div>
            <div className="p-3 rounded-xl bg-surface-900/50 border border-surface-700/30">
              <span className="text-surface-400 block mb-1">Updated At:</span>
              <span className="font-mono text-surface-300">{formatDate(memory.updated_at)}</span>
            </div>
          </div>

          <div className="p-3 rounded-xl bg-surface-900/50 border border-surface-700/30 space-y-1 font-mono text-[11px] text-surface-400">
            <p><span className="text-surface-500">ID:</span> {memory.id}</p>
            <p><span className="text-surface-500">Conversation ID:</span> {memory.conversation_id || 'N/A'}</p>
            <p><span className="text-surface-500">Vector Store ID:</span> {memory.id}</p>
          </div>
        </div>

        <div className="flex justify-end pt-2">
          <button onClick={onClose} className="btn-ghost text-xs">Close</button>
        </div>
      </motion.div>
    </div>
  );
}
