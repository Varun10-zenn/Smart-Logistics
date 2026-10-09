
import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, MapPin, Clock, Truck, Route, AlertTriangle, Play, Square } from 'lucide-react';
import { AppShell } from '../components/layout/AppShell';
import { SkeletonCard } from '../components/ui/Skeleton';
import { ErrorState } from '../components/ui/States';
import { StatusBadge, SeverityBadge } from '../components/ui/Badge';
import { deliveryApi } from '../api/deliveryApi';
import { safetyApi } from '../api/safetyApi';
import { RouteMap } from '../components/map/RouteMap';

export function DeliveryDetailPage() {
  const { id } = useParams<{ id: string }>();
  const deliveryId = Number(id);
  const queryClient = useQueryClient();
  const [profile, setProfile] = useState<'normal' | 'aggressive'>('normal');

  const delivery = useQuery({
    queryKey: ['delivery', deliveryId],
    queryFn: () => deliveryApi.get(deliveryId),
    enabled: !!deliveryId,
    refetchInterval: 5000, // Poll every 5s for live position and updates
  });

  const route = useQuery({
    queryKey: ['delivery', deliveryId, 'route'],
    queryFn: () => deliveryApi.getRoute(deliveryId),
    enabled: !!deliveryId,
    retry: false,
  });

  const eta = useQuery({
    queryKey: ['delivery', deliveryId, 'eta'],
    queryFn: () => deliveryApi.getEta(deliveryId),
    enabled: !!deliveryId,
    refetchInterval: 5000,
    retry: false,
  });

  const safetyScore = useQuery({
    queryKey: ['safety', 'score', deliveryId],
    queryFn: () => safetyApi.getScore(deliveryId),
    enabled: !!deliveryId,
    refetchInterval: 5000,
    retry: false,
  });

  const safetyAlerts = useQuery({
    queryKey: ['safety', 'alerts', deliveryId],
    queryFn: () => safetyApi.listAlerts({ page: 1, page_size: 10, delivery_id: deliveryId }),
    enabled: !!deliveryId,
    refetchInterval: 5000,
  });

  const simStatus = useQuery({
    queryKey: ['delivery', deliveryId, 'simulation'],
    queryFn: () => deliveryApi.getSimulationStatus(deliveryId),
    enabled: !!deliveryId,
    refetchInterval: 3000,
    retry: false,
  });

  const startSimMutation = useMutation({
    mutationFn: () => deliveryApi.startSimulation(deliveryId, profile),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['delivery', deliveryId, 'simulation'] });
    },
    onError: (err: any) => {
      const detail = err.response?.data?.detail;
      const msg = typeof detail === 'string' ? detail : detail?.message || err.message || 'Failed to start simulation.';
      alert(`[HTTP ${err.response?.status || 500}] ${msg}`);
    }
  });

  const stopSimMutation = useMutation({
    mutationFn: () => deliveryApi.stopSimulation(deliveryId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['delivery', deliveryId, 'simulation'] });
    },
  });

  if (delivery.isLoading) {
    return (
      <AppShell title="Delivery Detail">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-4xl mx-auto">
          {[1, 2, 3, 4].map((i) => <SkeletonCard key={i} />)}
        </div>
      </AppShell>
    );
  }

  if (delivery.isError) {
    return (
      <AppShell title="Delivery Detail">
        <ErrorState message="Could not load delivery." onRetry={() => delivery.refetch()} />
      </AppShell>
    );
  }

  const d = delivery.data!;
  const sim = simStatus.data;
  const isSimRunning = sim?.status === 'running';



  return (
    <AppShell title={`Delivery ${d.delivery_code}`}>
      <div className="space-y-4 max-w-4xl mx-auto">
        {/* Back */}
        <Link to="/deliveries" className="btn-ghost inline-flex items-center gap-1.5 text-sm">
          <ArrowLeft size={15} /> All deliveries
        </Link>

        {/* Header */}
        <div className="card p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="font-serif text-[22px] text-ink">{d.delivery_code}</h2>
            <p className="caption mt-0.5">Batch #{d.batch_id}</p>
          </div>
          <div className="flex items-center gap-3">
            <StatusBadge status={d.status} />
            {safetyScore.data && (
              <span className={`px-3 py-1 rounded-full text-xs font-bold font-mono border ${
                safetyScore.data.score >= 80
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                  : safetyScore.data.score >= 60
                  ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                  : 'bg-red-500/10 text-red-400 border-red-500/30'
              }`}>
                Safety Score: {safetyScore.data.score.toFixed(0)}
              </span>
            )}
          </div>
        </div>

        {/* Simulation Controls Panel */}
        {simStatus.isSuccess && (
          <div className="card p-4 bg-[#121824] border border-amber-500/30 rounded-2xl flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400">
                <Play size={18} />
              </div>
              <div>
                <h4 className="text-xs font-semibold text-white">Rider Telemetry Simulator</h4>
                <p className="text-[11px] text-slate-400">
                  Status: <span className="font-mono text-amber-400 uppercase font-bold">{sim?.status}</span>
                  {sim?.current_step !== undefined && ` · Step ${sim.current_step}/${sim.total_steps}`}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3 w-full sm:w-auto">
              <select
                value={profile}
                onChange={(e) => setProfile(e.target.value as any)}
                disabled={isSimRunning}
                className="bg-slate-900 border border-slate-800 text-xs text-slate-200 rounded-xl px-3 py-1.5"
              >
                <option value="normal">Normal Profile</option>
                <option value="aggressive">Aggressive (Speeding & Braking)</option>
              </select>

              {isSimRunning ? (
                <button
                  onClick={() => stopSimMutation.mutate()}
                  disabled={stopSimMutation.isPending}
                  className="px-3 py-1.5 bg-red-600 hover:bg-red-500 text-white text-xs font-medium rounded-xl flex items-center gap-1.5 cursor-pointer"
                >
                  <Square size={14} /> Stop Sim
                </button>
              ) : (
                <button
                  onClick={() => startSimMutation.mutate()}
                  disabled={startSimMutation.isPending}
                  className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded-xl flex items-center gap-1.5 cursor-pointer"
                >
                  <Play size={14} /> Start Sim
                </button>
              )}
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Assignment */}
          <div className="card p-5 space-y-3">
            <h3 className="section-title flex items-center gap-2">
              <Truck size={16} className="text-[#8FA6BE]" /> Assignment
            </h3>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="card-inset p-3">
                <p className="caption mb-1">Driver</p>
                <p className="font-medium text-ink">#{d.driver_id}</p>
              </div>
              <div className="card-inset p-3">
                <p className="caption mb-1">Vehicle</p>
                <p className="font-medium text-ink">#{d.vehicle_id}</p>
              </div>
              <div className="card-inset p-3">
                <p className="caption mb-1">Scheduled</p>
                <p className="font-medium text-ink text-xs">
                  {new Date(d.scheduled_dispatch_time).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}
                </p>
              </div>
              <div className="card-inset p-3">
                <p className="caption mb-1">Est. ETA</p>
                <p className="font-medium text-ink text-xs">
                  {d.estimated_eta
                    ? new Date(d.estimated_eta).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })
                    : 'Not calculated'}
                </p>
              </div>
            </div>
          </div>

          {/* Route info */}
          <div className="card p-5 space-y-3">
            <h3 className="section-title flex items-center gap-2">
              <Route size={16} className="text-[#88A594]" /> Route
            </h3>
            {route.isLoading && <div className="h-20 skeleton rounded" />}
            {route.isError && (
              <p className="caption text-ink-mute">No route generated yet.</p>
            )}
            {route.data && (
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="card-inset p-3">
                  <p className="caption mb-1">Distance</p>
                  <p className="font-medium text-ink">{route.data.total_distance_km.toFixed(1)} km</p>
                </div>
                <div className="card-inset p-3">
                  <p className="caption mb-1">Travel time</p>
                  <p className="font-medium text-ink">{Math.round(route.data.estimated_travel_minutes)} min</p>
                </div>
                <div className="card-inset p-3">
                  <p className="caption mb-1">Traffic factor</p>
                  <p className="font-medium text-ink">×{route.data.traffic_factor.toFixed(2)}</p>
                </div>
                <div className="card-inset p-3">
                  <p className="caption mb-1">Weather factor</p>
                  <p className="font-medium text-ink">×{route.data.weather_factor.toFixed(2)}</p>
                </div>
              </div>
            )}
          </div>

          {/* ETA detail */}
          {eta.data && (
            <div className="card p-5 space-y-3">
              <h3 className="section-title flex items-center gap-2">
                <Clock size={16} className="text-[#C0A063]" /> ETA Calculation
              </h3>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="card-inset p-3">
                  <p className="caption mb-1">ETA</p>
                  <p className="font-medium text-ink text-xs">
                    {new Date(eta.data.eta).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}
                  </p>
                </div>
                <div className="card-inset p-3">
                  <p className="caption mb-1">Base route</p>
                  <p className="font-medium text-ink">{Math.round(eta.data.base_route_minutes)} min</p>
                </div>
                <div className="card-inset p-3 col-span-2">
                  <p className="caption mb-1">Algorithm</p>
                  <p className="font-medium text-ink text-xs">{eta.data.algorithm}</p>
                </div>
              </div>
            </div>
          )}

          {/* Safety alerts */}
          <div className="card p-5 space-y-3">
            <h3 className="section-title flex items-center gap-2">
              <AlertTriangle size={16} className="text-[#C58783]" /> Safety Alerts
            </h3>
            {safetyAlerts.isLoading && <div className="h-20 skeleton rounded" />}
            {safetyAlerts.data?.items.length === 0 && (
              <p className="caption">No safety alerts for this delivery.</p>
            )}
            {safetyAlerts.data && safetyAlerts.data.items.length > 0 && (
              <div className="space-y-2 max-h-40 overflow-y-auto">
                {safetyAlerts.data.items.slice(0, 5).map((a) => (
                  <div key={a.id} className="card-inset p-3 flex items-center gap-3">
                    <SeverityBadge severity={a.severity} />
                    <p className="text-xs text-ink flex-1">{a.message}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Live OpenStreetMap / Leaflet Route Map */}
        <div className="card p-5 space-y-3">
          <h3 className="section-title flex items-center gap-2">
            <MapPin size={16} className="text-amber-400" /> Live Delivery Route Geometry
          </h3>

          <RouteMap
            routeGeometry={route.data?.route_geometry}
            simStep={sim?.current_step}
            riderName={`Rider #${d.driver_id}`}
            height="320px"
          />
        </div>
      </div>
    </AppShell>
  );
}
