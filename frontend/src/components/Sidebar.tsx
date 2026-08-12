/**
 * Sidebar: conversation list + new chat button.
 */
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  MessageSquarePlus, Trash2, Brain, Settings, LogOut, ChevronLeft,
  Search, MessageSquare, Archive, Star, MoreHorizontal, Terminal,
  Sun, Moon,
} from 'lucide-react';
import { conversationApi } from '@/lib/api';
import { useAuthStore, useUIStore } from '@/store';
import { relativeTime, truncate, cn } from '@/lib/utils';
import { Spinner, Tooltip } from '@/components/ui/shared';
import { toast } from '@/components/ui/Toast';
import type { Conversation } from '@/types';

interface SidebarProps {
  onNewChat: () => void;
}

export function Sidebar({ onNewChat }: SidebarProps) {
  const { user, clearAuth } = useAuthStore();
  const { sidebarOpen, setSidebarOpen, activeConversationId, setActiveConversation, theme, toggleTheme } = useUIStore();
  const [search, setSearch] = useState('');
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['conversations'],
    queryFn: () => conversationApi.list(1, 50),
    refetchInterval: 30_000,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => conversationApi.delete(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ['conversations'] });
      if (activeConversationId === id) setActiveConversation(null);
      toast.success('Conversation deleted');
      setDeleteTarget(null);
    },
    onError: () => toast.error('Failed to delete conversation'),
  });

  const conversations = data?.items ?? [];
  const filtered = search
    ? conversations.filter((c) => c.title.toLowerCase().includes(search.toLowerCase()))
    : conversations;

  const handleLogout = () => {
    clearAuth();
    window.location.href = '/login';
  };

  return (
    <>
      {/* Overlay on mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <motion.aside
        initial={false}
        animate={{ width: sidebarOpen ? 280 : 0, opacity: sidebarOpen ? 1 : 0 }}
        transition={{ type: 'spring', damping: 25, stiffness: 200 }}
        className="fixed md:relative left-0 top-0 h-screen z-40 flex-shrink-0 overflow-hidden
                   bg-surface-900 border-r border-surface-700/50 flex flex-col"
      >
        <div className="flex flex-col h-full w-[280px]">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-surface-700/50">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-brand-500 to-accent-purple flex items-center justify-center">
                <Brain className="w-4.5 h-4.5 text-white" />
              </div>
              <span className="font-bold text-surface-50 text-sm">MemoryAI</span>
            </div>
            <button onClick={() => setSidebarOpen(false)} className="btn-icon">
              <ChevronLeft className="w-4 h-4" />
            </button>
          </div>

          {/* New Chat */}
          <div className="p-3">
            <button
              id="new-chat-btn"
              onClick={onNewChat}
              className="btn-primary w-full justify-center gap-2 py-2.5"
            >
              <MessageSquarePlus className="w-4 h-4" />
              <span>New Chat</span>
            </button>
          </div>

          {/* Search */}
          <div className="px-3 pb-2">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-surface-500" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search conversations…"
                className="w-full bg-surface-800 border border-surface-700 rounded-xl pl-8 pr-3 py-2
                           text-xs text-surface-200 placeholder-surface-600
                           focus:outline-none focus:ring-1 focus:ring-brand-500/50"
              />
            </div>
          </div>

          {/* Conversation List */}
          <div className="flex-1 overflow-y-auto px-2 pb-2">
            {isLoading ? (
              <div className="flex justify-center py-8"><Spinner /></div>
            ) : filtered.length === 0 ? (
              <div className="text-center py-8">
                <MessageSquare className="w-8 h-8 text-surface-600 mx-auto mb-2" />
                <p className="text-xs text-surface-500">
                  {search ? 'No results found' : 'No conversations yet'}
                </p>
              </div>
            ) : (
              <AnimatePresence>
                {filtered.map((conv) => (
                  <ConvItem
                    key={conv.id}
                    conv={conv}
                    active={conv.id === activeConversationId}
                    onSelect={() => setActiveConversation(conv.id)}
                    onDelete={() => setDeleteTarget(conv.id)}
                    deleting={deleteMutation.isPending && deleteTarget === conv.id}
                  />
                ))}
              </AnimatePresence>
            )}
          </div>

          {/* Bottom nav */}
          <div className="border-t border-surface-700/50 p-3 space-y-1">
            <button
              onClick={() => toggleTheme()}
              className="sidebar-item w-full text-left flex items-center justify-between"
              title="Toggle Light / Dark mode"
            >
              <div className="flex items-center gap-3">
                {theme === 'dark' ? (
                  <Moon className="w-4 h-4 text-accent-purple" />
                ) : (
                  <Sun className="w-4 h-4 text-accent-gold" />
                )}
                <span>{theme === 'dark' ? 'Dark Mode' : 'Light Mode'}</span>
              </div>
              <div className="w-9 h-5 rounded-full bg-surface-700 p-0.5 transition-colors relative flex items-center">
                <div
                  className={cn(
                    'w-4 h-4 rounded-full bg-white shadow-md transition-transform duration-200',
                    theme === 'light' ? 'translate-x-4 bg-amber-400' : 'translate-x-0 bg-brand-400'
                  )}
                />
              </div>
            </button>
            <NavItem icon={<Brain className="w-4 h-4" />} label="Memory Dashboard" href="/memory" />
            <NavItem icon={<Terminal className="w-4 h-4" />} label="Prompt Debugger" href="/debugger" />
            <NavItem icon={<Settings className="w-4 h-4" />} label="Settings" href="/settings" />
            <button
              onClick={handleLogout}
              className="sidebar-item w-full text-left text-red-400 hover:text-red-300 hover:bg-red-500/10"
            >
              <LogOut className="w-4 h-4" />
              <span>Sign out</span>
            </button>
          </div>

          {/* User info */}
          {user && (
            <div className="p-3 border-t border-surface-700/50">
              <div className="flex items-center gap-2.5 px-2 py-2 rounded-xl bg-surface-800/50">
                <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-brand-500 to-accent-purple flex items-center justify-center text-xs font-bold text-white">
                  {user.username.slice(0, 2).toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-surface-200 truncate">{user.username}</p>
                  <p className="text-xs text-surface-500 truncate">{user.email}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </motion.aside>

      {/* Confirm delete dialog */}
      <AnimatePresence>
        {deleteTarget && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4"
            onClick={() => setDeleteTarget(null)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="glass rounded-2xl p-6 max-w-sm w-full"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-surface-50 font-semibold mb-2">Delete conversation?</h3>
              <p className="text-surface-400 text-sm mb-5">This action cannot be undone.</p>
              <div className="flex gap-3">
                <button onClick={() => setDeleteTarget(null)} className="btn-ghost flex-1">Cancel</button>
                <button
                  onClick={() => deleteMutation.mutate(deleteTarget)}
                  className="btn-danger flex-1 justify-center"
                  disabled={deleteMutation.isPending}
                >
                  {deleteMutation.isPending ? <Spinner size="sm" /> : 'Delete'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

function ConvItem({ conv, active, onSelect, onDelete, deleting }: {
  conv: Conversation;
  active: boolean;
  onSelect: () => void;
  onDelete: () => void;
  deleting: boolean;
}) {
  const [hover, setHover] = useState(false);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -10 }}
      className={cn('sidebar-item mb-0.5', active && 'active')}
      onClick={onSelect}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      <MessageSquare className={cn('w-4 h-4 shrink-0', active ? 'text-brand-400' : 'text-surface-600 group-hover:text-surface-400')} />
      <div className="flex-1 min-w-0">
        <p className="truncate text-xs font-medium">{conv.title || 'New conversation'}</p>
        <p className="text-xs text-surface-600">{relativeTime(conv.updated_at)}</p>
      </div>
      {hover && (
        <button
          onClick={(e) => { e.stopPropagation(); onDelete(); }}
          className="p-1 rounded-lg hover:bg-red-500/20 text-surface-500 hover:text-red-400 transition-colors"
          title="Delete"
        >
          {deleting ? <Spinner size="sm" /> : <Trash2 className="w-3.5 h-3.5" />}
        </button>
      )}
    </motion.div>
  );
}

function NavItem({ icon, label, href }: { icon: React.ReactNode; label: string; href: string }) {
  return (
    <a href={href} className="sidebar-item">
      {icon}
      <span>{label}</span>
    </a>
  );
}

// Collapsed sidebar toggle button
export function SidebarToggle() {
  const { sidebarOpen, setSidebarOpen } = useUIStore();
  if (sidebarOpen) return null;
  return (
    <Tooltip tip="Open sidebar">
      <button onClick={() => setSidebarOpen(true)} className="btn-icon p-2.5">
        <Brain className="w-5 h-5 text-brand-400" />
      </button>
    </Tooltip>
  );
}
