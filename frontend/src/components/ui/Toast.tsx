/**
 * Toast notification system.
 */
import { useState, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle, XCircle, AlertCircle, Info, X } from 'lucide-react';
import { cn } from '@/lib/utils';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  id: string;
  type: ToastType;
  message: string;
  duration?: number;
}

const icons = {
  success: <CheckCircle className="w-4 h-4 text-emerald-400" />,
  error:   <XCircle className="w-4 h-4 text-red-400" />,
  warning: <AlertCircle className="w-4 h-4 text-amber-400" />,
  info:    <Info className="w-4 h-4 text-cyan-400" />,
};

const colors = {
  success: 'border-emerald-500/30 bg-emerald-500/10',
  error:   'border-red-500/30 bg-red-500/10',
  warning: 'border-amber-500/30 bg-amber-500/10',
  info:    'border-cyan-500/30 bg-cyan-500/10',
};

// ── Global toast state ────────────────────────────────────────
let addToast: ((t: Omit<Toast, 'id'>) => void) | null = null;

export const toast = {
  success: (message: string, duration = 3000) => addToast?.({ type: 'success', message, duration }),
  error:   (message: string, duration = 5000) => addToast?.({ type: 'error',   message, duration }),
  warning: (message: string, duration = 4000) => addToast?.({ type: 'warning', message, duration }),
  info:    (message: string, duration = 3000) => addToast?.({ type: 'info',    message, duration }),
};

// ── Toast item ────────────────────────────────────────────────
function ToastItem({ toast: t, onRemove }: { toast: Toast; onRemove: (id: string) => void }) {
  useEffect(() => {
    const timer = setTimeout(() => onRemove(t.id), t.duration ?? 3000);
    return () => clearTimeout(timer);
  }, [t, onRemove]);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 50, scale: 0.9 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 20, scale: 0.9 }}
      className={cn(
        'flex items-center gap-3 px-4 py-3 rounded-xl border glass-dark shadow-xl',
        'min-w-[280px] max-w-[400px]',
        colors[t.type],
      )}
    >
      {icons[t.type]}
      <p className="text-sm text-surface-100 flex-1">{t.message}</p>
      <button onClick={() => onRemove(t.id)} className="btn-icon p-1">
        <X className="w-3.5 h-3.5" />
      </button>
    </motion.div>
  );
}

// ── Toast provider ────────────────────────────────────────────
export function ToastProvider() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const add = useCallback((t: Omit<Toast, 'id'>) => {
    const id = Math.random().toString(36).slice(2);
    setToasts((prev) => [...prev, { ...t, id }]);
  }, []);

  const remove = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  useEffect(() => {
    addToast = add;
    return () => { addToast = null; };
  }, [add]);

  return createPortal(
    <div className="fixed bottom-6 right-6 z-[9999] flex flex-col gap-2 pointer-events-none">
      <AnimatePresence mode="popLayout">
        {toasts.map((t) => (
          <div key={t.id} className="pointer-events-auto">
            <ToastItem toast={t} onRemove={remove} />
          </div>
        ))}
      </AnimatePresence>
    </div>,
    document.body,
  );
}
