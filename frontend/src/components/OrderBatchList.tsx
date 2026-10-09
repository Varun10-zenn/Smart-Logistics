import type { BatchSummaryDTO } from '../types/api';
import { Package, Route, Clock, Scale, Box, AlertTriangle } from 'lucide-react';

interface OrderBatchListProps {
  batches: BatchSummaryDTO[];
  unassignedOrderIds?: number[];
  unassignedReasons?: Record<number, string>;
  selectedBatchId?: number | null;
  onSelectBatch?: (batch: BatchSummaryDTO) => void;
}

export function OrderBatchList({
  batches,
  unassignedOrderIds = [],
  unassignedReasons = {},
  selectedBatchId,
  onSelectBatch,
}: OrderBatchListProps) {
  return (
    <div className="space-y-4">
      {/* Batches Grid */}
      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
          Generated Picking Batches ({batches.length})
        </h4>

        {batches.length === 0 ? (
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-center text-xs text-slate-400">
            No picking batches generated.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {batches.map((b) => {
              const isSelected = selectedBatchId === b.batch_id;
              return (
                <div
                  key={b.batch_id}
                  onClick={() => onSelectBatch?.(b)}
                  className={`p-4 rounded-xl border transition-all cursor-pointer ${
                    isSelected
                      ? 'border-indigo-500 bg-indigo-950/40 shadow-lg shadow-indigo-950/30'
                      : 'border-slate-800 bg-slate-900/50 hover:border-slate-700 hover:bg-slate-900/90'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2">
                      <span className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400">
                        <Package size={16} />
                      </span>
                      <span className="font-mono text-sm font-semibold text-slate-100">{b.batch_code}</span>
                    </div>
                    <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[11px] font-medium text-emerald-400">
                      {b.order_ids.length} Orders
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs text-slate-400 mt-3 pt-2 border-t border-slate-800/80">
                    <div className="flex items-center gap-1.5">
                      <Route size={14} className="text-slate-500" />
                      <span>{b.total_distance_meters}m</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Clock size={14} className="text-slate-500" />
                      <span>{b.estimated_duration_minutes} mins</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Scale size={14} className="text-slate-500" />
                      <span>{b.total_weight_kg} kg</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Box size={14} className="text-slate-500" />
                      <span>{b.total_volume_cbm} cbm</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Unassigned Orders Warning Panel */}
      {unassignedOrderIds.length > 0 && (
        <div className="p-4 rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-300 space-y-2">
          <div className="flex items-center gap-2 font-medium text-xs">
            <AlertTriangle size={16} className="text-amber-400 shrink-0" />
            <span>Unassigned Orders ({unassignedOrderIds.length})</span>
          </div>
          <div className="space-y-1 text-xs text-amber-200/90 pl-6">
            {unassignedOrderIds.map((oid) => (
              <div key={oid} className="flex items-start gap-2">
                <span className="font-mono text-amber-400">Order #{oid}:</span>
                <span>{unassignedReasons[oid] || 'Did not meet batch constraints or inventory stock requirements.'}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
