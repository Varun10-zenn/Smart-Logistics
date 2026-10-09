import React from 'react';
import { Inbox, AlertCircle, WifiOff } from 'lucide-react';

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="p-4 rounded-full bg-surface-2 border border-line mb-4">
        <Inbox size={24} className="text-ink-mute" />
      </div>
      <p className="section-title text-ink-mute mb-1">{title}</p>
      {description && <p className="caption mt-1 max-w-xs">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
}

export function ErrorState({ message = 'Failed to load data.', onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="p-4 rounded-full bg-[#8C4A47]/10 border border-[#8C4A47]/30 mb-4">
        <AlertCircle size={24} className="text-[#C58783]" />
      </div>
      <p className="section-title text-[#C58783] mb-1">Error</p>
      <p className="caption mt-1 max-w-xs">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="btn-secondary mt-4">
          Retry
        </button>
      )}
    </div>
  );
}

export function OfflineState({ lastKnown }: { lastKnown?: string }) {
  return (
    <div className="flex items-center gap-3 px-4 py-3 rounded-input bg-[#8A6A34]/10 border border-[#8A6A34]/30 text-[#C0A063]">
      <WifiOff size={16} />
      <div>
        <span className="text-sm font-medium">Unable to load data.</span>
        {lastKnown && (
          <span className="caption ml-2">Showing last known state from {lastKnown}.</span>
        )}
      </div>
    </div>
  );
}
