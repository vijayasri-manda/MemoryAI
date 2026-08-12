/**
 * Individual chat message component with actions.
 */
import { useState } from 'react';
import { motion } from 'framer-motion';
import { Copy, Check, RotateCcw, Edit2, ThumbsUp, ThumbsDown, Sparkles } from 'lucide-react';
import { MarkdownRenderer } from '@/components/ui/MarkdownRenderer';
import { Avatar, Badge, Tooltip, TypingIndicator } from '@/components/ui/shared';
import { copyToClipboard, formatDate, cn } from '@/lib/utils';
import type { Message, MemorySearchResult } from '@/types';

interface MessageBubbleProps {
  message: Message;
  onRegenerate?: () => void;
  onEdit?: (content: string) => void;
  memoriesUsed?: MemorySearchResult[];
  isStreaming?: boolean;
}

export function MessageBubble({ message, onRegenerate, onEdit, memoriesUsed, isStreaming }: MessageBubbleProps) {
  const [copied, setCopied] = useState(false);
  const [showMemories, setShowMemories] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState(message.content);
  const isUser = message.role === 'user';

  const handleCopy = async () => {
    const ok = await copyToClipboard(message.content);
    if (ok) { setCopied(true); setTimeout(() => setCopied(false), 2000); }
  };

  const handleEditSave = () => {
    if (editText.trim() && editText !== message.content) {
      onEdit?.(editText);
    }
    setEditing(false);
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className={cn('flex gap-3 group', isUser && 'flex-row-reverse')}
    >
      {/* Avatar */}
      <Avatar isAI={!isUser} name={isUser ? 'You' : undefined} size="sm" />

      {/* Content */}
      <div className={cn('flex flex-col gap-1 max-w-[80%]', isUser && 'items-end')}>
        {/* Memories used indicator */}
        {!isUser && memoriesUsed && memoriesUsed.length > 0 && (
          <button
            onClick={() => setShowMemories((s) => !s)}
            className="flex items-center gap-1.5 text-xs text-brand-400/80 hover:text-brand-400 transition-colors mb-1"
          >
            <Sparkles className="w-3 h-3" />
            <span>{memoriesUsed.length} memor{memoriesUsed.length === 1 ? 'y' : 'ies'} retrieved</span>
          </button>
        )}

        {/* Memory context (collapsible) */}
        {showMemories && memoriesUsed && memoriesUsed.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="glass rounded-xl p-3 mb-1 space-y-2 text-xs max-w-full"
          >
            <p className="text-surface-400 font-medium">Retrieved Memories:</p>
            {memoriesUsed.map((m, idx) => (
              <div key={m.memory?.id ?? idx} className="flex items-start gap-2 p-2 rounded-lg bg-surface-800/50">
                <div className="shrink-0 w-1 h-1 rounded-full bg-brand-400 mt-1.5" />
                <div className="flex-1 min-w-0">
                  <p className="text-surface-300 line-clamp-2">{m.memory?.content ?? ''}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="brand">{(m.similarity_score * 100).toFixed(0)}% match</Badge>
                    {m.memory?.tags?.slice(0, 2).map((tag: string) => (
                      <Badge key={tag}>{tag}</Badge>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </motion.div>
        )}

        {/* Message bubble */}
        <div className={cn(isUser ? 'msg-user' : 'msg-assistant', 'relative')}>
          {editing ? (
            <div className="space-y-2">
              <textarea
                value={editText}
                onChange={(e) => setEditText(e.target.value)}
                rows={3}
                className="w-full bg-transparent text-sm text-surface-100 resize-none outline-none min-w-[200px]"
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleEditSave(); }
                  if (e.key === 'Escape') setEditing(false);
                }}
              />
              <div className="flex gap-2 justify-end">
                <button onClick={() => setEditing(false)} className="text-xs text-surface-400 hover:text-surface-200">Cancel</button>
                <button onClick={handleEditSave} className="btn-primary text-xs py-1 px-3">Save & Submit</button>
              </div>
            </div>
          ) : isStreaming ? (
            <TypingIndicator />
          ) : isUser ? (
            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          ) : (
            <MarkdownRenderer content={message.content} />
          )}
        </div>

        {/* Timestamp */}
        <p className="text-xs text-surface-600 px-1">{formatDate(message.created_at)}</p>

        {/* Actions (appear on hover) */}
        {!isStreaming && (
          <div className={cn(
            'flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-150',
            isUser && 'flex-row-reverse',
          )}>
            <Tooltip tip="Copy">
              <button onClick={handleCopy} className="btn-icon p-1.5">
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            </Tooltip>
            {isUser && onEdit && (
              <Tooltip tip="Edit & Resubmit">
                <button onClick={() => { setEditing(true); setEditText(message.content); }} className="btn-icon p-1.5">
                  <Edit2 className="w-3.5 h-3.5" />
                </button>
              </Tooltip>
            )}
            {!isUser && onRegenerate && (
              <Tooltip tip="Regenerate">
                <button onClick={onRegenerate} className="btn-icon p-1.5">
                  <RotateCcw className="w-3.5 h-3.5" />
                </button>
              </Tooltip>
            )}
            {!isUser && (
              <>
                <Tooltip tip="Good response">
                  <button className="btn-icon p-1.5"><ThumbsUp className="w-3.5 h-3.5" /></button>
                </Tooltip>
                <Tooltip tip="Bad response">
                  <button className="btn-icon p-1.5"><ThumbsDown className="w-3.5 h-3.5" /></button>
                </Tooltip>
              </>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
}

// Streaming placeholder bubble
export function StreamingBubble({ content }: { content: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex gap-3"
    >
      <Avatar isAI size="sm" />
      <div className="msg-assistant max-w-[80%]">
        {content ? (
          <MarkdownRenderer content={content} />
        ) : (
          <TypingIndicator />
        )}
        <span className="inline-block w-0.5 h-4 bg-brand-400 animate-pulse ml-0.5" />
      </div>
    </motion.div>
  );
}
