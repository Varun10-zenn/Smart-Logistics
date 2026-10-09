import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Brain, Send, AlertCircle } from 'lucide-react';
import { AppShell } from '../components/layout/AppShell';
import { intelligenceApi } from '../api/intelligenceApi';
import type { IntelligenceResponse } from '../types/api';

const PRESETS = [
  { label: 'Charging recommendation', query: 'Recommend the best charging station for a vehicle with low battery.' },
  { label: 'Safety overview', query: 'Summarize the current safety status across all deliveries.' },
  { label: 'Warehouse efficiency', query: 'How can warehouse picking efficiency be improved today?' },
  { label: 'Delivery delays', query: 'Which deliveries are most likely to be delayed?' },
];

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  return (
    <div className="space-y-1">
      <div className="flex justify-between caption">
        <span>Confidence</span>
        <span className="text-ink font-medium">{pct}%</span>
      </div>
      <div className="h-1.5 rounded-full bg-surface-2 overflow-hidden">
        <div
          className="h-full rounded-full bg-grad-lead"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export function AIInsightsPage() {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<IntelligenceResponse | null>(null);

  const mutation = useMutation({
    mutationFn: intelligenceApi.query,
    onSuccess: (data) => setResult(data),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setResult(null);
    mutation.mutate({ query });
  };

  const apiError = mutation.error as any;
  const apiErrorMsg =
    apiError?.response?.data?.error?.message ||
    apiError?.response?.data?.detail?.message ||
    apiError?.message ||
    'Failed to get a response.';

  return (
    <AppShell title="AI Insights">
      <div className="max-w-2xl mx-auto space-y-5">
        <div>
          <h2 className="font-serif text-[22px] text-ink flex items-center gap-2">
            <Brain size={20} className="text-[#8FA6BE]" />
            AI Insights
          </h2>
          <p className="caption mt-1">
            Query the logistics intelligence layer. Results include reasoning, confidence, and supporting inputs.
          </p>
        </div>

        {/* Presets */}
        <div className="flex flex-wrap gap-2">
          {PRESETS.map((p) => (
            <button
              key={p.label}
              onClick={() => setQuery(p.query)}
              className="btn-ghost text-xs px-3 py-1.5 border border-line"
            >
              {p.label}
            </button>
          ))}
        </div>

        {/* Input */}
        <form onSubmit={handleSubmit} className="card p-4 space-y-3">
          <label htmlFor="ai-query" className="section-title">
            Ask the intelligence layer
          </label>
          <textarea
            id="ai-query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            rows={3}
            className="w-full px-3 py-2.5 rounded-input bg-surface-2 border border-line text-ink placeholder:text-ink-mute text-sm focus:outline-none focus:ring-2 focus:ring-[#8FA6BE] resize-none"
            placeholder="e.g. Which vehicles need charging within the next hour?"
          />
          <button
            type="submit"
            disabled={mutation.isPending || !query.trim()}
            className="btn-primary flex items-center gap-2 text-sm"
          >
            {mutation.isPending ? (
              <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <Send size={14} />
            )}
            {mutation.isPending ? 'Thinking…' : 'Ask'}
          </button>
        </form>

        {/* Error */}
        {mutation.isError && (
          <div className="flex items-start gap-2 p-3 rounded-input bg-[#8C4A47]/10 border border-[#8C4A47]/30 text-[#C58783] text-sm">
            <AlertCircle size={15} className="mt-0.5 shrink-0" />
            <span>{apiErrorMsg}</span>
          </div>
        )}

        {/* Result */}
        {result && (
          <div className="card p-5 space-y-4">
            {/* AI recommendation card matching spec */}
            <div className="flex items-center justify-between">
              <h3 className="section-title flex items-center gap-2">
                <Brain size={16} className="text-[#8FA6BE]" />
                AI Recommendation
              </h3>
              {result.fallback && (
                <span className="badge-warn">Deterministic fallback</span>
              )}
            </div>

            <div className="card-inset p-4 space-y-2">
              <p className="body-text text-ink leading-relaxed">{result.recommendation}</p>
            </div>

            <ConfidenceBar value={result.confidence} />

            <div>
              <p className="caption font-medium text-ink mb-1">Reasoning</p>
              <p className="body-text text-ink-mute text-sm leading-relaxed">{result.reasoning}</p>
            </div>

            {result.metadata && Object.keys(result.metadata).length > 0 && (
              <div>
                <p className="caption font-medium text-ink mb-2">Supporting inputs</p>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(result.metadata).map(([k, v]) => (
                    <div key={k} className="card-inset p-2.5">
                      <p className="caption capitalize">{k.replace(/_/g, ' ')}</p>
                      <p className="text-sm text-ink font-medium truncate">{String(v)}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Limitation note */}
        <div className="card-inset p-4">
          <p className="caption">
            <strong className="text-ink">Note:</strong> The intelligence layer is deterministic.
            It does not use an uncontrolled LLM and does not access the database directly.
            All data in responses comes from backend services.
          </p>
        </div>
      </div>
    </AppShell>
  );
}
