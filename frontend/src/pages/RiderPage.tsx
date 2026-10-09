import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Truck, MapPin, CheckCircle2, Play, LogOut, Clock, ShieldCheck, Navigation, BatteryCharging, Zap, Square } from 'lucide-react';
import { deliveryApi } from '../api/deliveryApi';
import { chargingApi } from '../api/chargingApi';
import { useAuth } from '../contexts/AuthContext';
import { RouteMap } from '../components/map/RouteMap';

export function RiderPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: activeDeliveries, isLoading, refetch } = useQuery({
    queryKey: ['rider-active-deliveries'],
    queryFn: deliveryApi.getRiderActive,
    refetchInterval: 5000,
  });

  const activeDelivery = activeDeliveries && activeDeliveries.length > 0 ? activeDeliveries[0] : null;

  const { data: chargingRec } = useQuery({
    queryKey: ['charging-recommendation', activeDelivery?.id],
    queryFn: () => deliveryApi.getChargingRecommendation(activeDelivery!.id),
    enabled: !!activeDelivery,
    refetchInterval: 5000,
  });

  const { data: simState, refetch: refetchSim } = useQuery({
    queryKey: ['delivery-sim-state', activeDelivery?.id],
    queryFn: () => deliveryApi.getSimulationStatus(activeDelivery!.id),
    enabled: !!activeDelivery,
    refetchInterval: 3000,
  });

  const startMutation = useMutation({
    mutationFn: (deliveryId: number) => deliveryApi.startDelivery(deliveryId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rider-active-deliveries'] });
      refetch();
    },
    onError: (err: any) => {
      alert(err.response?.data?.detail?.message || 'Failed to start delivery.');
    },
  });

  const deliverStopMutation = useMutation({
    mutationFn: ({ deliveryId, stopId }: { deliveryId: number; stopId: number }) =>
      deliveryApi.deliverStop(deliveryId, stopId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rider-active-deliveries'] });
      refetch();
    },
    onError: (err: any) => {
      alert(err.response?.data?.detail?.message || 'Failed to complete delivery stop.');
    },
  });

  const startSimMutation = useMutation({
    mutationFn: (profile: 'normal' | 'aggressive') =>
      deliveryApi.startSimulation(activeDelivery!.id, profile),
    onSuccess: () => {
      refetchSim();
    },
    onError: (err: any) => {
      const detail = err.response?.data?.detail;
      const msg = typeof detail === 'string' ? detail : detail?.message || err.message || 'Failed to start simulation';
      alert(`[HTTP ${err.response?.status || 500}] ${msg}`);
    },
  });

  const stopSimMutation = useMutation({
    mutationFn: () => deliveryApi.stopSimulation(activeDelivery!.id),
    onSuccess: () => {
      refetchSim();
    },
  });

  const reserveSlotMutation = useMutation({
    mutationFn: (slotId: number) =>
      chargingApi.createReservation({
        slot_id: slotId,
        vehicle_id: activeDelivery?.vehicle_id,
        driver_id: user?.id || 1,
        delivery_id: activeDelivery?.id,
      }),
    onSuccess: () => {
      alert('Charging slot successfully reserved!');
      queryClient.invalidateQueries({ queryKey: ['charging-recommendation', activeDelivery?.id] });
    },
    onError: (err: any) => {
      alert(err.response?.data?.detail?.message || 'Failed to reserve slot');
    },
  });

  return (
    <div className="min-h-screen bg-[#0B0F17] text-slate-100 font-sans flex flex-col">
      {/* Mobile Top Navbar */}
      <header className="sticky top-0 z-30 bg-[#121824]/95 backdrop-blur-md border-b border-slate-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-amber-500 to-yellow-400 flex items-center justify-center text-white shadow-lg shadow-amber-500/20">
            <Truck size={20} />
          </div>
          <div>
            <h1 className="font-serif text-base font-semibold text-white">Rider Dispatch</h1>
            <p className="text-[11px] text-slate-400">{user?.full_name || user?.email}</p>
          </div>
        </div>

        <button
          onClick={async () => {
            await logout();
            navigate('/staff/login');
          }}
          className="p-2 rounded-xl text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-colors"
          title="Log Out"
        >
          <LogOut size={18} />
        </button>
      </header>

      {/* Main Body */}
      <main className="flex-1 max-w-lg w-full mx-auto p-4 space-y-4">
        {isLoading && (
          <div className="p-8 text-center text-xs text-slate-400 flex items-center justify-center gap-2">
            <div className="w-4 h-4 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
            <span>Fetching assigned deliveries...</span>
          </div>
        )}

        {!isLoading && !activeDelivery && (
          <div className="card p-8 bg-[#121824] border border-slate-800 rounded-2xl text-center space-y-3">
            <div className="w-12 h-12 rounded-full bg-slate-900 text-amber-400 flex items-center justify-center mx-auto border border-slate-800">
              <ShieldCheck size={24} />
            </div>
            <h3 className="text-base font-serif text-white">No Active Delivery Run</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              You currently have no active assigned delivery batches. Standing by for auto-handoff when darkstore batches finish picking.
            </p>
            <button
              onClick={() => refetch()}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs font-medium rounded-xl text-slate-200 cursor-pointer"
            >
              Check for New Dispatch
            </button>
          </div>
        )}

        {activeDelivery && (
          <div className="space-y-4">
            {/* Low Battery Alert Banner & Recommendation */}
            {chargingRec && chargingRec.recommended_station && (
              <div className="card p-4 bg-amber-500/10 border border-amber-500/40 rounded-2xl space-y-3 animate-pulse">
                <div className="flex items-center gap-2 text-amber-400">
                  <BatteryCharging size={20} className="shrink-0" />
                  <div className="flex-1">
                    <span className="text-xs font-bold uppercase tracking-wide">Low EV Battery Warning</span>
                    <p className="text-[11px] text-amber-200/90">
                      Charge recommended at <strong>{chargingRec.recommended_station.name}</strong> ({chargingRec.recommended_station.distance_km} km away).
                    </p>
                  </div>
                </div>
                {chargingRec.recommended_slot && (
                  <div className="bg-[#121824]/90 p-2.5 rounded-xl text-xs border border-amber-500/20 flex items-center justify-between">
                    <div>
                      <span className="text-slate-400 text-[10px] block">Available Slot</span>
                      <span className="font-mono text-white font-medium">
                        {new Date(chargingRec.recommended_slot.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} - {new Date(chargingRec.recommended_slot.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <button
                      onClick={() => reserveSlotMutation.mutate(chargingRec.recommended_slot.id)}
                      disabled={reserveSlotMutation.isPending}
                      className="px-3 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs rounded-lg cursor-pointer transition-all shadow-md"
                    >
                      Reserve Slot
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Rider Telemetry Simulator Control Panel */}
            <div className="card p-4 bg-[#121824] border border-cyan-500/30 rounded-2xl space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Zap size={16} className="text-cyan-400" />
                  <span className="text-xs font-semibold text-white">Rider Route Telemetry Simulator</span>
                </div>
                <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                  simState?.is_running ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 animate-pulse' : 'bg-slate-800 text-slate-400'
                }`}>
                  {simState?.is_running ? 'Sim Active' : 'Idle'}
                </span>
              </div>

              {simState?.is_running ? (
                <div className="flex items-center justify-between pt-1">
                  <div className="text-[11px] font-mono text-cyan-300">
                    Progress: {simState.progress_percent}% | Speed: {simState.current_speed_kmh} km/h
                  </div>
                  <button
                    onClick={() => stopSimMutation.mutate()}
                    className="px-3 py-1 bg-red-600 hover:bg-red-500 text-white font-medium text-xs rounded-lg flex items-center gap-1 cursor-pointer"
                  >
                    <Square size={12} />
                    <span>Stop Sim</span>
                  </button>
                </div>
              ) : (
                <div className="flex gap-2 pt-1">
                  <button
                    onClick={() => startSimMutation.mutate('normal')}
                    disabled={startSimMutation.isPending || activeDelivery.status !== 'in_transit'}
                    className="flex-1 py-1.5 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-40 text-white font-medium text-xs rounded-xl flex items-center justify-center gap-1 cursor-pointer"
                  >
                    <Play size={13} />
                    <span>Sim Normal Drive</span>
                  </button>
                  <button
                    onClick={() => startSimMutation.mutate('aggressive')}
                    disabled={startSimMutation.isPending || activeDelivery.status !== 'in_transit'}
                    className="flex-1 py-1.5 bg-rose-600 hover:bg-rose-500 disabled:opacity-40 text-white font-medium text-xs rounded-xl flex items-center justify-center gap-1 cursor-pointer"
                  >
                    <Zap size={13} />
                    <span>Sim Aggressive Drive</span>
                  </button>
                </div>
              )}
            </div>

            {/* Delivery Card Summary */}
            <div className="card p-5 bg-[#121824] border border-amber-500/30 rounded-2xl space-y-4 shadow-xl">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-[10px] font-mono uppercase tracking-wider text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                    {activeDelivery.delivery_code}
                  </span>
                  <h2 className="text-sm font-semibold text-white mt-1">Multi-Stop Delivery Route</h2>
                </div>
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase ${
                  activeDelivery.status === 'in_transit'
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                    : 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                }`}>
                  {activeDelivery.status.replace('_', ' ')}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3 text-xs p-3 rounded-xl bg-slate-900/90 border border-slate-800">
                <div>
                  <span className="text-slate-500 text-[11px] block">Assigned Vehicle</span>
                  <span className="font-mono text-amber-400 font-semibold">{activeDelivery.vehicle_code || `Vehicle #${activeDelivery.vehicle_id}`}</span>
                </div>
                <div>
                  <span className="text-slate-500 text-[11px] block">Driver</span>
                  <span className="font-mono text-slate-200 font-semibold">{activeDelivery.driver_name || user?.full_name || `Driver #${activeDelivery.driver_id}`}</span>
                </div>
                <div>
                  <span className="text-slate-500 text-[11px] block">Total Distance</span>
                  <span className="font-mono text-slate-200 font-semibold">{activeDelivery.total_distance_km} km</span>
                </div>
                <div>
                  <span className="text-slate-500 text-[11px] block">Est. Duration</span>
                  <span className="font-mono text-slate-200 font-semibold">{activeDelivery.estimated_travel_minutes} mins</span>
                </div>
              </div>

              {activeDelivery.status !== 'in_transit' && (
                <button
                  onClick={() => startMutation.mutate(activeDelivery.id)}
                  disabled={startMutation.isPending}
                  className="w-full py-3 bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white font-semibold text-xs rounded-xl shadow-lg shadow-emerald-600/20 flex items-center justify-center gap-2 cursor-pointer transition-all disabled:opacity-50"
                >
                  <Play size={16} />
                  <span>Start Delivery Run</span>
                </button>
              )}

              {/* Shared Live Route Map */}
              <RouteMap
                routeGeometry={activeDelivery.route_geometry}
                simStep={simState?.current_step}
                riderName={user?.full_name || 'Rider'}
                height="240px"
              />
            </div>

            {/* Stops Sequence */}
            <div className="space-y-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                <Navigation size={14} className="text-amber-400" />
                <span>Customer Delivery Stops ({activeDelivery.stops.length})</span>
              </h3>

              {activeDelivery.stops.map((stop: any) => {
                const isDelivered = stop.status === 'delivered';
                return (
                  <div
                    key={stop.id}
                    className={`card p-4 rounded-2xl border transition-all ${
                      isDelivered
                        ? 'bg-slate-900/40 border-slate-800 text-slate-500'
                        : 'bg-[#121824] border-slate-800 text-slate-100 shadow-md'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-start gap-3">
                        <div
                          className={`w-7 h-7 rounded-lg text-xs font-bold flex items-center justify-center shrink-0 mt-0.5 ${
                            isDelivered ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'
                          }`}
                        >
                          #{stop.stop_sequence}
                        </div>
                        <div className="space-y-1">
                          <h4 className="text-xs font-semibold text-white">{stop.customer_name}</h4>
                          <p className="text-[11px] text-slate-400 leading-relaxed flex items-center gap-1">
                            <MapPin size={12} className="text-slate-500 shrink-0" />
                            <span>{stop.destination_address}</span>
                          </p>
                          <div className="flex items-center gap-2 pt-1 text-[10px] text-slate-400 font-mono">
                            <Clock size={11} className="text-slate-500" />
                            <span>ETA: {new Date(stop.estimated_arrival).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                          </div>
                        </div>
                      </div>

                      <div>
                        {isDelivered ? (
                          <span className="px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-[11px] font-semibold flex items-center gap-1">
                            <CheckCircle2 size={13} />
                            <span>Done</span>
                          </span>
                        ) : (
                          <button
                            onClick={() => deliverStopMutation.mutate({ deliveryId: activeDelivery.id, stopId: stop.id })}
                            disabled={deliverStopMutation.isPending || activeDelivery.status !== 'in_transit'}
                            className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-xl shadow cursor-pointer disabled:opacity-40 transition-all"
                          >
                            Mark Delivered
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

