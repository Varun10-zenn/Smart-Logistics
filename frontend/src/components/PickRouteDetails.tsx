import type { BatchSummaryDTO } from '../types/api';
import { Navigation } from 'lucide-react';

interface PickRouteDetailsProps {
  batch: BatchSummaryDTO;
}

export function PickRouteDetails({ batch }: PickRouteDetailsProps) {
  return (
    <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Navigation size={18} className="text-sky-400" />
          <h4 className="font-semibold text-sm text-slate-100">
            Pick Route Sequence — {batch.batch_code}
          </h4>
        </div>
        <span className="px-2 py-0.5 rounded bg-sky-500/10 text-sky-400 text-xs font-mono">
          {batch.algorithm_used}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2 text-xs text-slate-300 p-2.5 rounded-lg bg-slate-800/60">
        <div>
          <span className="text-slate-400 block text-[10px]">Total Walk</span>
          <span className="font-semibold">{batch.total_distance_meters}m</span>
        </div>
        <div>
          <span className="text-slate-400 block text-[10px]">Est. Time</span>
          <span className="font-semibold">{batch.estimated_duration_minutes} mins</span>
        </div>
        <div>
          <span className="text-slate-400 block text-[10px]">Stops</span>
          <span className="font-semibold">{batch.steps_count} stops</span>
        </div>
      </div>

      <div className="text-xs text-slate-400 leading-relaxed">
        Sequence paths are visually rendered on the layout canvas above with dashed amber routes.
      </div>
    </div>
  );
}
