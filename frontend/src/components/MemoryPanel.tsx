/**
 * Memory panel — shows retrieved/stored memories.
 */
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { X, Brain, Search, Trash2, Star, Tag, Clock, TrendingUp } from 'lucide-react';
import { memoryApi } from '@/lib/api';
import { useUIStore } from '@/store';
import { Badge, Progress, EmptyState, Spinner } from '@/components/ui/shared';
import { toast } from '@/components/ui/Toast';
import { formatDate, truncate, cn, importanceLabel } from '@/lib/utils';
import type { Memory } from '@/types';

export function MemoryPanel() {
  const { memoryPanelOpen, setMemoryPanelOpen } = useUIStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTag, setSelectedTag] = useState<string | undefined>();
  const [page, setPage] = useState(1);
  const qc = useQueryClient();

  const { data: stats } = useQuery({
    queryKey: ['memory-stats'],
    queryFn: memoryApi.stats,
    enabled: memoryPanelOpen,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['memories', page, selectedTag],
    queryFn: () => memoryApi.list(page, 15, selectedTag),
    enabled: memoryPanelOpen,
  });

  const { data: searchData, isLoading: searching } = useQuery({
    queryKey: ['memory-search', searchQuery],
    queryFn: () => memoryApi.search(searchQuery, 10),
    enabled: searchQuery.length > 2,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => memoryApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['memories'] });
      qc.invalidateQueries({ queryKey: ['memory-stats'] });
      toast.success('Memory deleted');
    },
    onError: () => toast.error('Failed to delete memory'),
  });

  const memories: Memory[] = searchQuery.length > 2
    ? (searchData?.results?.map((r) => r.memory) ?? [])
    : (data?.items ?? []);
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 1;

  const allTags = stats ? Object.keys(stats.by_type) : [];

  return (
    <AnimatePresence>
      {memoryPanelOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/40 z-40"
            onClick={() => setMemoryPanelOpen(false)}
          />

          {/* Panel */}
          <motion.aside
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed right-0 top-0 h-screen w-[420px] max-w-full z-50
                       bg-surface-900 border-l border-surface-700/50 flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-5 border-b border-surface-700/50">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-accent-purple to-brand-500 flex items-center justify-center">
                  <Brain className="w-4 h-4 text-white" />
                </div>
                <div>
                  <h2 className="font-semibold text-surface-50 text-sm">Memory Vault</h2>
                  <p className="text-xs text-surface-500">{total} memories stored</p>
                </div>
              </div>
              <button onClick={() => setMemoryPanelOpen(false)} className="btn-icon">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Stats */}
            {stats && (
              <div className="p-4 grid grid-cols-2 gap-3 border-b border-surface-700/50">
                <StatCard icon={<Brain className="w-4 h-4 text-brand-400" />} label="Total Memories" value={stats.total_memories} />
                <StatCard icon={<TrendingUp className="w-4 h-4 text-emerald-400" />} label="Avg Importance" value={`${(stats.avg_importance * 100).toFixed(0)}%`} />
              </div>
            )}

            {/* Search */}
            <div className="p-4 border-b border-surface-700/50 space-y-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-500" />
                <input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Semantic search memories…"
                  className="w-full bg-surface-800 border border-surface-700 rounded-xl pl-10 pr-4 py-2.5
                             text-sm text-surface-200 placeholder-surface-600
                             focus:outline-none focus:ring-1 focus:ring-brand-500/50"
                />
                {searching && <Spinner size="sm" className="absolute right-3 top-1/2 -translate-y-1/2" />}
              </div>

              {/* Tag filters */}
              {allTags.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  <button
                    onClick={() => setSelectedTag(undefined)}
                    className={cn('memory-badge border transition-colors', selectedTag === undefined
                      ? 'bg-brand-500/20 text-brand-300 border-brand-500/30'
                      : 'bg-surface-800 text-surface-400 border-surface-700 hover:border-brand-500/30')}
                  >
                    All
                  </button>
                  {allTags.slice(0, 8).map((tag) => (
                    <button
                      key={tag}
                      onClick={() => setSelectedTag(tag === selectedTag ? undefined : tag)}
                      className={cn('memory-badge border transition-colors', selectedTag === tag
                        ? 'bg-brand-500/20 text-brand-300 border-brand-500/30'
                        : 'bg-surface-800 text-surface-400 border-surface-700 hover:border-brand-500/30')}
                    >
                      <Tag className="w-2.5 h-2.5" />
                      {tag}
                      <span className="text-surface-600">{stats?.by_type[tag]}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Memory list */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {isLoading ? (
                <div className="flex justify-center py-8"><Spinner /></div>
              ) : memories.length === 0 ? (
                <EmptyState
                  icon={<Brain className="w-8 h-8" />}
                  title="No memories yet"
                  description="Start chatting — the AI will automatically extract and store important memories."
                />
              ) : (
                memories.map((memory) => (
                  <MemoryCard
                    key={memory.id}
                    memory={memory}
                    onDelete={() => deleteMutation.mutate(memory.id)}
                    isDeleting={deleteMutation.isPending && deleteMutation.variables === memory.id}
                  />
                ))
              )}
            </div>

            {/* Pagination */}
            {!searchQuery && pages > 1 && (
              <div className="flex items-center justify-between p-4 border-t border-surface-700/50">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="btn-ghost text-xs py-1.5 px-3"
                >Previous</button>
                <span className="text-xs text-surface-500">Page {page} / {pages}</span>
                <button
                  onClick={() => setPage((p) => Math.min(pages, p + 1))}
                  disabled={page === pages}
                  className="btn-ghost text-xs py-1.5 px-3"
                >Next</button>
              </div>
            )}
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}

function MemoryCard({ memory, onDelete, isDeleting }: {
  memory: Memory;
  onDelete: () => void;
  isDeleting: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const level = memory.importance_score >= 0.7 ? 'high' : memory.importance_score >= 0.4 ? 'medium' : 'low';
  const levelClass = { high: 'importance-high', medium: 'importance-medium', low: 'importance-low' }[level];

  return (
    <motion.div
      layout
      className="card-hover"
      onClick={() => setExpanded((s) => !s)}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <p className={cn('text-sm text-surface-200', !expanded && 'line-clamp-2')}>
          {memory.content}
        </p>
        <button
          onClick={(e) => { e.stopPropagation(); onDelete(); }}
          className="btn-icon p-1 shrink-0 text-surface-600 hover:text-red-400"
        >
          {isDeleting ? <Spinner size="sm" /> : <Trash2 className="w-3.5 h-3.5" />}
        </button>
      </div>

      {/* Importance bar */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-surface-500">Importance</span>
          <span className={cn('memory-badge border text-xs', levelClass)}>
            <Star className="w-2.5 h-2.5" />
            {importanceLabel(memory.importance_score)}
          </span>
        </div>
        <Progress
          value={memory.importance_score}
          colorClass={level === 'high' ? 'bg-red-400' : level === 'medium' ? 'bg-amber-400' : 'bg-surface-500'}
        />
      </div>

      {/* Tags */}
      {memory.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {memory.tags.map((tag) => (
            <Badge key={tag} variant="brand">{tag}</Badge>
          ))}
        </div>
      )}

      {/* Meta */}
      <div className="flex items-center gap-3 text-xs text-surface-600">
        <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{formatDate(memory.created_at)}</span>
        {memory.access_count > 0 && (
          <span>{memory.access_count} uses</span>
        )}
      </div>
    </motion.div>
  );
}

function StatCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string | number }) {
  return (
    <div className="bg-surface-800/50 rounded-xl p-3 border border-surface-700/30">
      <div className="flex items-center gap-2 mb-1">{icon}<span className="text-xs text-surface-500">{label}</span></div>
      <p className="text-lg font-bold text-surface-50">{value}</p>
    </div>
  );
}
