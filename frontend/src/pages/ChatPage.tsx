/**
 * Main Chat page — full ChatGPT-style interface with streaming + RAG memory.
 */
import { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Menu, Brain, Download, Trash2, MoreVertical, Sparkles } from 'lucide-react';
import { Sidebar, SidebarToggle } from '@/components/Sidebar';
import { MessageBubble, StreamingBubble } from '@/components/MessageBubble';
import { ChatInput } from '@/components/ChatInput';
import { MemoryPanel } from '@/components/MemoryPanel';
import { EmptyState, Spinner, Tooltip } from '@/components/ui/shared';
import { toast } from '@/components/ui/Toast';
import { conversationApi, streamChat } from '@/lib/api';
import { useUIStore } from '@/store';
import { cn, genId } from '@/lib/utils';
import type { Message, MemorySearchResult } from '@/types';

// Placeholder messages for demonstration when backend isn't connected
const WELCOME_SUGGESTIONS = [
  "What programming languages do I prefer?",
  "Summarize my recent projects",
  "What were my goals from our last conversation?",
  "Remind me about my coding style preferences",
];

export function ChatPage() {
  const {
    sidebarOpen, setSidebarOpen, toggleSidebar,
    activeConversationId, setActiveConversation,
    memoryPanelOpen, toggleMemoryPanel,
  } = useUIStore();

  const [messages, setMessages] = useState<Message[]>([]);
  const [streamingContent, setStreamingContent] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [memoriesForMessages, setMemoriesForMessages] = useState<Record<string, MemorySearchResult[]>>({});
  const [memoryEnabled, setMemoryEnabled] = useState(true);
  const [conversationMemories, setConversationMemories] = useState<MemorySearchResult[]>([]);

  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const qc = useQueryClient();

  // Load messages when conversation changes
  const { data: loadedMessages, isLoading: loadingMessages } = useQuery({
    queryKey: ['messages', activeConversationId],
    queryFn: () => conversationApi.messages(activeConversationId!),
    enabled: !!activeConversationId,
  });

  useEffect(() => {
    if (loadedMessages) {
      setMessages(loadedMessages);
    }
  }, [loadedMessages]);

  // Auto-scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  // New chat
  const handleNewChat = useCallback(() => {
    setActiveConversation(null);
    setMessages([]);
    setStreamingContent('');
    setConversationMemories([]);
    setMemoriesForMessages({});
  }, [setActiveConversation]);

  // Send message with streaming
  const handleSend = useCallback(async (userMessage: string) => {
    if (isStreaming) return;

    // Optimistically add user message
    const tempId = genId();
    const userMsg: Message = {
      id: tempId,
      conversation_id: activeConversationId ?? '',
      role: 'user',
      content: userMessage,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsStreaming(true);
    setStreamingContent('');

    const ctrl = new AbortController();
    abortRef.current = ctrl;

    let assistantContent = '';
    const assistantId = genId();

    try {
      await streamChat(
        userMessage,
        activeConversationId ?? undefined,
        // onChunk
        (chunk) => {
          assistantContent += chunk;
          setStreamingContent(assistantContent);
        },
        // onMemories
        (memories) => {
          setConversationMemories(memories);
          setMemoriesForMessages((prev) => ({ ...prev, [assistantId]: memories }));
        },
        // onDone
        (_reason) => {
          const assistantMsg: Message = {
            id: assistantId,
            conversation_id: activeConversationId ?? '',
            role: 'assistant',
            content: assistantContent,
            created_at: new Date().toISOString(),
          };
          setMessages((prev) => [...prev, assistantMsg]);
          setStreamingContent('');
          setIsStreaming(false);
          qc.invalidateQueries({ queryKey: ['conversations'] });
          qc.invalidateQueries({ queryKey: ['memory-stats'] });
        },
        // onError
        (err) => {
          toast.error(`AI error: ${err}`);
          setIsStreaming(false);
          setStreamingContent('');
        },
        ctrl.signal,
      );
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        toast.error('Connection error. Is the backend running?');
      }
      setIsStreaming(false);
      setStreamingContent('');
    }
  }, [activeConversationId, isStreaming, qc]);

  const handleStop = () => {
    abortRef.current?.abort();
    if (streamingContent) {
      const assistantMsg: Message = {
        id: genId(),
        conversation_id: activeConversationId ?? '',
        role: 'assistant',
        content: streamingContent + ' [stopped]',
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    }
    setStreamingContent('');
    setIsStreaming(false);
  };

  const handleRegenerate = useCallback(() => {
    const lastUser = [...messages].reverse().find((m) => m.role === 'user');
    if (lastUser) {
      setMessages((prev) => prev.slice(0, -1)); // remove last assistant msg
      handleSend(lastUser.content);
    }
  }, [messages, handleSend]);

  const handleEditAndSend = useCallback((messageId: string, newContent: string) => {
    const idx = messages.findIndex((m) => m.id === messageId);
    if (idx === -1) return;
    setMessages((prev) => prev.slice(0, idx)); // remove from this message onwards
    handleSend(newContent);
  }, [messages, handleSend]);

  return (
    <div className="flex h-screen bg-surface-950 overflow-hidden">
      {/* Sidebar */}
      <Sidebar onNewChat={handleNewChat} />

      {/* Main area */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Header */}
        <header className="flex items-center justify-between px-4 py-3 border-b border-surface-700/50
                           bg-surface-950/80 backdrop-blur-lg shrink-0">
          <div className="flex items-center gap-3">
            {!sidebarOpen && (
              <button onClick={toggleSidebar} className="btn-icon" id="sidebar-toggle-btn">
                <Menu className="w-5 h-5" />
              </button>
            )}
            <SidebarToggle />
            <div>
              <h1 className="text-sm font-semibold text-surface-100">
                {activeConversationId ? 'Conversation' : 'New Chat'}
              </h1>
              {conversationMemories.length > 0 && (
                <p className="text-xs text-brand-400/80 flex items-center gap-1">
                  <Sparkles className="w-3 h-3" />
                  {conversationMemories.length} memories active
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Memory vault button */}
            <Tooltip tip="Memory Vault">
              <button
                onClick={toggleMemoryPanel}
                id="memory-panel-btn"
                className={cn(
                  'btn-icon relative',
                  memoryPanelOpen && 'bg-brand-500/15 text-brand-400',
                )}
              >
                <Brain className="w-5 h-5" />
                {conversationMemories.length > 0 && (
                  <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-brand-400 animate-pulse" />
                )}
              </button>
            </Tooltip>

            {activeConversationId && (
              <Tooltip tip="Export conversation">
                <button className="btn-icon">
                  <Download className="w-4.5 h-4.5" />
                </button>
              </Tooltip>
            )}
          </div>
        </header>

        {/* Messages area */}
        <div className="flex-1 overflow-y-auto">
          {loadingMessages ? (
            <div className="flex justify-center py-16"><Spinner size="lg" /></div>
          ) : messages.length === 0 && !isStreaming ? (
            <WelcomeScreen onSuggest={handleSend} />
          ) : (
            <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
              <AnimatePresence initial={false}>
                {messages.map((msg) => (
                  <MessageBubble
                    key={msg.id}
                    message={msg}
                    memoriesUsed={memoriesForMessages[msg.id]}
                    onRegenerate={msg.role === 'assistant' ? handleRegenerate : undefined}
                    onEdit={msg.role === 'user'
                      ? (newContent) => handleEditAndSend(msg.id, newContent)
                      : undefined}
                  />
                ))}
              </AnimatePresence>

              {/* Streaming bubble */}
              {isStreaming && <StreamingBubble content={streamingContent} />}

              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {/* Chat input */}
        <ChatInput
          onSend={handleSend}
          onStop={handleStop}
          isStreaming={isStreaming}
          memoryEnabled={memoryEnabled}
          onToggleMemory={() => setMemoryEnabled((s) => !s)}
        />
      </div>

      {/* Memory panel */}
      <MemoryPanel />
    </div>
  );
}

function WelcomeScreen({ onSuggest }: { onSuggest: (msg: string) => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center h-full py-16 px-4"
    >
      {/* Animated brain icon */}
      <div className="relative mb-8">
        <div className="w-24 h-24 rounded-3xl bg-gradient-to-br from-brand-500 to-accent-purple
          flex items-center justify-center animate-glow shadow-2xl shadow-brand-500/30">
          <Brain className="w-12 h-12 text-white animate-float" />
        </div>
        <div className="absolute -top-2 -right-2 w-8 h-8 rounded-xl bg-accent-cyan/20 border border-accent-cyan/30
          flex items-center justify-center animate-pulse-slow">
          <Sparkles className="w-4 h-4 text-accent-cyan" />
        </div>
      </div>

      <h2 className="text-3xl font-bold mb-2">
        <span className="gradient-text">AI Memory Assistant</span>
      </h2>
      <p className="text-surface-400 text-center max-w-md mb-2 text-sm leading-relaxed">
        I remember everything from our previous conversations.
        Ask me anything — I'll retrieve relevant context automatically.
      </p>

      {/* Feature badges */}
      <div className="flex flex-wrap justify-center gap-2 mb-8">
        {['Persistent Memory', 'Semantic Search', 'RAG Pipeline', 'Multi-session'].map((f) => (
          <span key={f} className="text-xs px-3 py-1 rounded-full bg-surface-800/80 border border-surface-700/50 text-surface-400">
            {f}
          </span>
        ))}
      </div>

      {/* Suggestion prompts */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-xl w-full">
        {WELCOME_SUGGESTIONS.map((s) => (
          <motion.button
            key={s}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => onSuggest(s)}
            className="card-hover text-left text-sm text-surface-300 p-4 rounded-xl"
          >
            <Sparkles className="w-3.5 h-3.5 text-brand-400 mb-2" />
            {s}
          </motion.button>
        ))}
      </div>
    </motion.div>
  );
}
