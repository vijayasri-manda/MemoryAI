import React from 'react';
import { cn } from '@/lib/utils';

interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const sizes = { sm: 'w-4 h-4', md: 'w-6 h-6', lg: 'w-10 h-10' };
const borders = { sm: 'border-2', md: 'border-2', lg: 'border-3' };

export function Spinner({ size = 'md', className }: SpinnerProps) {
  return (
    <div
      className={cn(
        'rounded-full border-surface-600 border-t-brand-400 animate-spin',
        sizes[size],
        borders[size],
        className,
      )}
      aria-label="Loading"
    />
  );
}

export function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 px-4 py-3">
      <div className="typing-dot" />
      <div className="typing-dot" />
      <div className="typing-dot" />
    </div>
  );
}

interface AvatarProps {
  name?: string;
  src?: string;
  size?: 'sm' | 'md' | 'lg';
  isAI?: boolean;
}

export function Avatar({ name, src, size = 'md', isAI }: AvatarProps) {
  const szClass = { sm: 'w-7 h-7 text-xs', md: 'w-9 h-9 text-sm', lg: 'w-12 h-12 text-base' }[size];
  const initials = name?.slice(0, 2).toUpperCase() ?? 'U';

  if (isAI) {
    return (
      <div className={cn('rounded-xl flex items-center justify-center shrink-0', szClass,
        'bg-gradient-to-br from-brand-500 to-accent-purple')}>
        <span className="text-white font-bold">AI</span>
      </div>
    );
  }

  if (src) {
    return <img src={src} alt={name} className={cn('rounded-xl object-cover shrink-0', szClass)} />;
  }

  return (
    <div className={cn('rounded-xl flex items-center justify-center shrink-0 font-semibold',
      szClass, 'bg-surface-700 text-surface-300')}>
      {initials}
    </div>
  );
}

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'brand' | 'success' | 'warning' | 'danger' | 'info';
  className?: string;
}

const badgeVariants = {
  default:  'bg-surface-700/60 text-surface-300 border-surface-600/30',
  brand:    'bg-brand-500/15 text-brand-300 border-brand-500/20',
  success:  'bg-emerald-500/15 text-emerald-400 border-emerald-500/20',
  warning:  'bg-amber-500/15 text-amber-400 border-amber-500/20',
  danger:   'bg-red-500/15 text-red-400 border-red-500/20',
  info:     'bg-cyan-500/15 text-cyan-400 border-cyan-500/20',
};

export function Badge({ children, variant = 'default', className }: BadgeProps) {
  return (
    <span className={cn('memory-badge border', badgeVariants[variant], className)}>
      {children}
    </span>
  );
}

interface TooltipProps {
  children: React.ReactNode;
  tip: string;
}

export function Tooltip({ children, tip }: TooltipProps) {
  return (
    <div className="relative group">
      {children}
      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 rounded-lg
        bg-surface-700 text-surface-100 text-xs whitespace-nowrap
        opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity duration-200 z-50 border border-surface-600/50">
        {tip}
        <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-surface-700" />
      </div>
    </div>
  );
}

interface EmptyStateProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  action?: React.ReactNode;
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center animate-fade-in">
      <div className="w-16 h-16 rounded-2xl bg-surface-800 flex items-center justify-center mb-4 text-surface-500">
        {icon}
      </div>
      <h3 className="text-surface-200 font-semibold text-base mb-1">{title}</h3>
      <p className="text-surface-500 text-sm max-w-xs">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

interface ProgressProps {
  value: number; // 0–1
  className?: string;
  colorClass?: string;
}

export function Progress({ value, className, colorClass = 'bg-brand-500' }: ProgressProps) {
  return (
    <div className={cn('h-1.5 bg-surface-700 rounded-full overflow-hidden', className)}>
      <div
        className={cn('h-full rounded-full transition-all duration-500', colorClass)}
        style={{ width: `${Math.min(100, Math.max(0, value * 100))}%` }}
      />
    </div>
  );
}
