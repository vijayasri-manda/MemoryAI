/**
 * Chat input area with auto-resize, keyboard shortcuts.
 */
import { useRef, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Send, Square, Paperclip, Mic, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ChatInputProps {
  onSend: (message: string) => void;
  onStop?: () => void;
  isStreaming?: boolean;
  disabled?: boolean;
  placeholder?: string;
  memoryEnabled?: boolean;
  onToggleMemory?: () => void;
}

export function ChatInput({
  onSend, onStop, isStreaming, disabled, placeholder, memoryEnabled = true, onToggleMemory,
}: ChatInputProps) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [value]);

  const handleSend = () => {
    const msg = value.trim();
    if (!msg || (disabled && !isStreaming)) return;
    if (isStreaming) { onStop?.(); return; }
    onSend(msg);
    setValue('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const canSend = value.trim().length > 0 && !disabled;

  return (
    <div className="border-t border-surface-700/50 bg-surface-950/80 backdrop-blur-lg p-4">
      {/* Memory indicator */}
      <div className="flex items-center gap-2 mb-2">
        <button
          onClick={onToggleMemory}
          className={cn(
            'flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border transition-all duration-200',
            memoryEnabled
              ? 'bg-brand-500/15 text-brand-400 border-brand-500/30 hover:bg-brand-500/25'
              : 'bg-surface-800 text-surface-500 border-surface-700 hover:border-surface-600',
          )}
          title={memoryEnabled ? 'Memory ON — relevant memories will be retrieved' : 'Memory OFF'}
        >
          <Sparkles className={cn('w-3 h-3', memoryEnabled && 'animate-pulse-slow')} />
          <span>{memoryEnabled ? 'Memory Active' : 'Memory Off'}</span>
        </button>
      </div>

      {/* Input area */}
      <div className={cn(
        'flex items-end gap-3 glass rounded-2xl px-4 py-3 transition-all duration-200',
        'focus-within:border-brand-500/40 focus-within:ring-1 focus-within:ring-brand-500/20',
      )}>
        <textarea
          ref={textareaRef}
          id="chat-input"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder ?? 'Ask anything… your memories are always with you'}
          rows={1}
          disabled={disabled}
          className="flex-1 bg-transparent text-sm text-surface-100 placeholder-surface-600
                     resize-none outline-none max-h-[200px] leading-relaxed"
        />

        <div className="flex items-center gap-1.5 shrink-0">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleSend}
            disabled={!canSend && !isStreaming}
            id="send-btn"
            className={cn(
              'w-9 h-9 rounded-xl flex items-center justify-center transition-all duration-200',
              isStreaming
                ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30 border border-red-500/30'
                : canSend
                ? 'bg-brand-500 text-white hover:bg-brand-400 shadow-lg shadow-brand-500/25'
                : 'bg-surface-700 text-surface-500 cursor-not-allowed',
            )}
          >
            {isStreaming ? <Square className="w-4 h-4" /> : <Send className="w-4 h-4" />}
          </motion.button>
        </div>
      </div>

      <p className="text-xs text-surface-600 mt-2 text-center">
        Press <kbd className="px-1 py-0.5 rounded bg-surface-800 text-surface-400 text-xs font-mono">Enter</kbd> to send,{' '}
        <kbd className="px-1 py-0.5 rounded bg-surface-800 text-surface-400 text-xs font-mono">Shift+Enter</kbd> for new line
      </p>
    </div>
  );
}
