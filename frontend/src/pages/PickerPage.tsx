import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  CheckCircle2,
  PackageCheck,
  RefreshCw,
  MapPin,
  LogOut,
  ArrowLeft,
  AlertTriangle,
  Layers,
  ChevronRight
} from 'lucide-react';
import { pickingApi } from '../api/pickingApi';
import { warehouseApi } from '../api/warehouseApi';
import { WarehouseGraphCanvas } from '../components/WarehouseGraphCanvas';
import { useAuth } from '../contexts/AuthContext';

export function PickerPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [selectedBatchId, setSelectedBatchId] = useState<number | null>(null);
  const [completeError, setCompleteError] = useState<string | null>(null);

  // 1. Fetch Batches List (Polls every 5s)
  const {
    data: batchesData,
    isLoading: isBatchesLoading,
    refetch: refetchBatches,
  } = useQuery({
    queryKey: ['batches-picker', user?.warehouse_id],
    queryFn: () => pickingApi.listBatches({ page_size: 50, warehouse_id: user?.warehouse_id || undefined }),
    refetchInterval: 5000,
  });

  const batches = batchesData?.items || [];

  // 2. Fetch Selected Batch Pick Route
  const {
    data: pickRoute,
    isLoading: isRouteLoading,
    isError: isRouteError,
    refetch: refetchRoute,
  } = useQuery({
    queryKey: ['pick-route', selectedBatchId],
    queryFn: () => pickingApi.getBatchPickRoute(selectedBatchId!),
    enabled: !!selectedBatchId,
    refetchInterval: 5000,
  });

  // Find corresponding warehouse ID for canvas layout
  const selectedBatchObj = batches.find((b) => b.id === selectedBatchId);
  const warehouseId = selectedBatchObj?.warehouse_id;

  // 3. Fetch Warehouse Graph for Canvas Visualization
  const { data: graphData } = useQuery({
    queryKey: ['warehouse-graph-picker', warehouseId],
    queryFn: () => warehouseApi.getGraph(warehouseId!),
    enabled: !!warehouseId,
  });

  // Steps calculation
  const steps = pickRoute?.steps || [];
  const completedStepsCount = steps.filter((s) => s.is_completed).length;
  const totalStepsCount = steps.length;
  const progressPct = totalStepsCount > 0 ? Math.round((completedStepsCount / totalStepsCount) * 100) : 0;

  // Find the NEXT incomplete step
  const activeNextStepIndex = steps.findIndex((s) => !s.is_completed);
  const activeNextStep = activeNextStepIndex !== -1 ? steps[activeNextStepIndex] : null;
  const isBatchFinished = totalStepsCount > 0 && completedStepsCount === totalStepsCount;

  // 4. Complete Step Mutation
  const completeStepMutation = useMutation({
    mutationFn: (stepId: number) => pickingApi.completeStep(stepId),
    onSuccess: () => {
      setCompleteError(null);
      queryClient.invalidateQueries({ queryKey: ['pick-route', selectedBatchId] });
      queryClient.invalidateQueries({ queryKey: ['batches-picker'] });
    },
    onError: (err: any) => {
      console.error(err);
      const msg =
        err.response?.data?.error?.message ||
        err.response?.data?.detail?.message ||
        err.response?.data?.detail ||
        'Unable to complete pick step due to inventory stock mismatch.';
      setCompleteError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    },
  });

  const handleMarkStepPicked = (stepId: number) => {
    setCompleteError(null);
    completeStepMutation.mutate(stepId);
  };

  return (
    <div className="min-h-screen bg-[#0B0F17] text-slate-100 font-sans flex flex-col">
      {/* Mobile-Friendly Top Navigation */}
      <header className="sticky top-0 z-30 bg-[#121824]/95 backdrop-blur-md border-b border-slate-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {selectedBatchId ? (
            <button
              onClick={() => {
                setSelectedBatchId(null);
                setCompleteError(null);
              }}
              className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
            >
              <ArrowLeft size={18} />
            </button>
          ) : (
            <div className="p-2 rounded-xl bg-gradient-to-tr from-amber-500 to-orange-400 text-white shadow-lg shadow-amber-500/20">
              <PackageCheck size={20} />
            </div>
          )}
          <div>
            <h1 className="font-serif text-base font-semibold text-white">
              {selectedBatchId ? `Batch Picking #${selectedBatchObj?.batch_code || selectedBatchId}` : 'Picker Task Center'}
            </h1>
            <p className="text-[11px] text-slate-400">
              {selectedBatchId ? 'Darkstore Pick Route Execution' : 'Mobile Order Fulfillment Portal'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              refetchBatches();
              if (selectedBatchId) refetchRoute();
            }}
            className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            title="Refresh"
          >
            <RefreshCw size={16} />
          </button>
          {user && (
            <button
              onClick={async () => {
                await logout();
                navigate('/login');
              }}
              className="p-2 rounded-xl bg-slate-800 hover:bg-red-500/10 text-slate-400 hover:text-red-400 transition-colors"
              title="Log Out"
            >
              <LogOut size={16} />
            </button>
          )}
        </div>
      </header>

      {/* Main Content Area */}
      <div className="flex-1 max-w-5xl w-full mx-auto p-4 sm:p-6 space-y-6">
        
        {/* ─── BATCHES SELECTION LIST VIEW ────────────────────────────────────── */}
        {!selectedBatchId && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Assigned Batches ({batches.length})
              </h2>
              <span className="text-[11px] text-slate-400">Auto-Refreshes every 5s</span>
            </div>

            {isBatchesLoading && (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-24 rounded-2xl bg-[#121824] border border-slate-800 p-4 animate-pulse" />
                ))}
              </div>
            )}

            {batches.length === 0 && !isBatchesLoading && (
              <div className="card p-10 bg-[#121824] border border-slate-800 rounded-2xl text-center space-y-3">
                <div className="w-12 h-12 rounded-full bg-slate-900 text-slate-600 flex items-center justify-center mx-auto">
                  <Layers size={24} />
                </div>
                <p className="text-xs text-slate-400">No active picking batches available. New customer orders will be automatically batched into routes every 30 seconds.</p>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {batches.map((batch) => {
                const isCompleted = batch.status === 'completed';

                return (
                  <div
                    key={batch.id}
                    onClick={() => setSelectedBatchId(batch.id)}
                    className={`p-5 rounded-2xl border flex flex-col justify-between gap-4 cursor-pointer transition-all hover:scale-[1.01] ${
                      isCompleted
                        ? 'bg-[#0E131D] border-slate-800/80 opacity-70'
                        : 'bg-[#121824] border-slate-800 hover:border-slate-700 shadow-xl'
                    }`}
                  >
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-base font-bold text-white tracking-tight">
                          {batch.batch_code}
                        </span>
                        <span
                          className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            isCompleted
                              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                              : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                          }`}
                        >
                          {batch.status.replace('_', ' ').toUpperCase()}
                        </span>
                      </div>

                      <div className="flex items-center gap-3 text-xs text-slate-400">
                        <span>{batch.order_ids?.length || 0} Orders</span>
                        <span>•</span>
                        <span>Warehouse #{batch.warehouse_id}</span>
                      </div>
                    </div>

                    <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-300">
                      <span>{isCompleted ? 'Batch Completed' : 'Start Pick Route'}</span>
                      <ChevronRight size={16} className="text-slate-400" />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ─── ACTIVE BATCH PICK ROUTE EXECUTION VIEW ────────────────────────── */}
        {selectedBatchId && (
          <div className="space-y-6">
            
            {/* Error Notification */}
            {completeError && (
              <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/30 text-red-300 text-xs flex items-start gap-2">
                <AlertTriangle size={18} className="shrink-0 mt-0.5" />
                <span>{completeError}</span>
              </div>
            )}

            {/* Batch Complete Banner */}
            {isBatchFinished && (
              <div className="p-6 rounded-2xl bg-gradient-to-r from-emerald-950/60 to-teal-950/60 border border-emerald-500/30 text-center space-y-3 shadow-2xl animate-fade-in">
                <div className="w-12 h-12 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto">
                  <CheckCircle2 size={28} />
                </div>
                <h2 className="text-lg font-serif text-white font-semibold">Batch Complete - All Orders Picked!</h2>
                <p className="text-xs text-slate-300">All storage locations have been picked and stock deducted successfully.</p>
                <button
                  onClick={() => setSelectedBatchId(null)}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-xl transition-colors cursor-pointer inline-flex items-center gap-2"
                >
                  <ArrowLeft size={16} />
                  <span>Return to Batch List</span>
                </button>
              </div>
            )}

            {/* Progress Header Card */}
            <div className="card p-5 bg-[#121824] border border-slate-800 rounded-2xl space-y-3 shadow-xl">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400 uppercase tracking-wider font-semibold">
                  Picking Progress
                </span>
                <span className="font-mono text-emerald-400 font-bold text-sm">
                  {completedStepsCount} / {totalStepsCount} Steps ({progressPct}%)
                </span>
              </div>

              {/* Sticky Bar */}
              <div className="w-full h-3 bg-slate-900 rounded-full overflow-hidden border border-slate-800">
                <div
                  className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 transition-all duration-300"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
            </div>

            {/* Layout Canvas Visualization */}
            {graphData && (
              <div className="card p-4 bg-[#121824] border border-slate-800 rounded-2xl space-y-2">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span className="flex items-center gap-1.5 font-medium text-slate-300">
                    <MapPin size={14} className="text-emerald-400" />
                    <span>Darkstore Map View</span>
                  </span>
                  {activeNextStep && (
                    <span className="text-emerald-400 font-mono">
                      Current Target Location: <strong>{activeNextStep.location_code}</strong>
                    </span>
                  )}
                </div>

                <div className="h-64 w-full rounded-xl overflow-hidden bg-slate-950 border border-slate-900">
                  <WarehouseGraphCanvas
                    nodes={graphData.nodes}
                    edges={graphData.edges}
                    locations={graphData.locations}
                    highlightNodeIds={activeNextStep ? [activeNextStep.node_id] : []}
                  />
                </div>
              </div>
            )}

            {/* Steps List */}
            {isRouteLoading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-20 bg-[#121824] border border-slate-800 rounded-2xl animate-pulse" />
                ))}
              </div>
            ) : isRouteError ? (
              <div className="p-6 bg-amber-500/10 border border-amber-500/30 rounded-2xl text-amber-300 text-xs text-center space-y-2">
                <p>Pick route is currently being calculated or unavailable.</p>
                <button
                  onClick={() => refetchRoute()}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-white rounded-lg"
                >
                  Retry Loading
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Sequential Pick Steps ({steps.length})
                </h3>

                {steps.map((step, idx) => {
                  const isCompleted = step.is_completed;
                  const isActiveNext = idx === activeNextStepIndex;

                  return (
                    <div
                      key={step.id}
                      className={`p-4 sm:p-5 rounded-2xl border transition-all flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 ${
                        isCompleted
                          ? 'bg-[#0E131D] border-slate-800/80 opacity-70'
                          : isActiveNext
                          ? 'bg-gradient-to-r from-slate-900 to-[#161F30] border-emerald-500/60 shadow-xl ring-2 ring-emerald-500/20'
                          : 'bg-[#121824] border-slate-800/60 opacity-50'
                      }`}
                    >
                      <div className="flex items-start gap-3.5 min-w-0">
                        {/* Step Number Badge */}
                        <div
                          className={`w-9 h-9 rounded-xl flex items-center justify-center text-xs font-bold shrink-0 mt-0.5 ${
                            isCompleted
                              ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                              : isActiveNext
                              ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/30'
                              : 'bg-slate-800 text-slate-400 border border-slate-700'
                          }`}
                        >
                          {isCompleted ? <CheckCircle2 size={18} /> : step.step_number}
                        </div>

                        <div className="space-y-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-mono text-base font-bold text-white bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
                              {step.location_code}
                            </span>
                            <span className="text-xs font-medium text-slate-200 truncate">
                              {step.product_name || `Product #${step.product_id}`}
                            </span>
                          </div>

                          <div className="flex items-center gap-3 text-xs text-slate-400">
                            <span>
                              Pick Quantity: <strong className="text-emerald-300 font-mono text-sm">{step.quantity_to_pick}</strong> units
                            </span>
                            <span>•</span>
                            <span className="font-mono text-[11px]">SKU: {step.product_sku}</span>
                          </div>
                        </div>
                      </div>

                      {/* Action Button */}
                      <div>
                        {isCompleted ? (
                          <span className="text-xs text-emerald-400 font-medium flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                            <CheckCircle2 size={15} />
                            <span>Picked</span>
                          </span>
                        ) : isActiveNext ? (
                          <button
                            type="button"
                            onClick={() => handleMarkStepPicked(step.id)}
                            disabled={completeStepMutation.isPending}
                            className="w-full sm:w-auto min-w-[140px] py-3 px-5 bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white font-bold text-sm rounded-xl shadow-lg shadow-emerald-600/30 flex items-center justify-center gap-2 transition-all cursor-pointer disabled:opacity-50"
                          >
                            {completeStepMutation.isPending ? (
                              <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            ) : (
                              <>
                                <CheckCircle2 size={18} />
                                <span>Mark Picked</span>
                              </>
                            )}
                          </button>
                        ) : (
                          <span className="text-xs text-slate-500 italic px-3 py-1">
                            Locked
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}
