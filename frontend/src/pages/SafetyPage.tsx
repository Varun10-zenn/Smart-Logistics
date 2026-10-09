import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ShieldAlert, CheckCircle } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { AppShell } from '../components/layout/AppShell';
import { KpiCard } from '../components/ui/KpiCard';
import { SkeletonCard, SkeletonTable } from '../components/ui/Skeleton';
import { ErrorState, EmptyState } from '../components/ui/States';
import { SeverityBadge } from '../components/ui/Badge';
import { Link } from 'react-router-dom';
import { safetyApi } from '../api/safetyApi';
import { deliveryApi } from '../api/deliveryApi';

export function SafetyPage() {
  const [alertPage, setAlertPage] = useState(1);
  const [showAcknowledged, setShowAcknowledged] = useState(false);
  const qc = useQueryClient();

  const activeDeliveries = useQuery({
    queryKey: ['deliveries', 'in_transit'],
    queryFn: () => deliveryApi.list({ page: 1, status: 'in_transit' }),
    refetchInterval: 5000,
  });

  const alerts = useQuery({
    queryKey: ['safety', 'alerts', alertPage, showAcknowledged],
    queryFn: () => safetyApi.listAlerts({ page: alertPage, page_size: 10, acknowledged: showAcknowledged ? undefined : false }),
    refetchInterval: 5000, // Refreshes every 5 seconds as required
  });

  const events = useQuery({
    queryKey: ['safety', 'events'],
    queryFn: () => safetyApi.listEvents({ page: 1, page_size: 50 }),
    staleTime: 30_000,
  });

  const scores = useQuery({
    queryKey: ['safety', 'scores'],
    queryFn: () => safetyApi.listScores({ page: 1, page_size: 20 }),
    staleTime: 60_000,
  });

  const ackMutation = useMutation({
    mutationFn: (alertId: number) => safetyApi.acknowledgeAlert(alertId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['safety', 'alerts'] });
    },
  });

  // Build event-type chart data from real API events
  const eventChartData = useMemo(() => {
    if (!events.data) return [];
    const counts: Record<string, number> = {};
    for (const e of events.data.items) {
      counts[e.event_type] = (counts[e.event_type] ?? 0) + 1;
    }
    return Object.entries(counts).map(([type, count]) => ({ type: type.replace(/_/g, ' '), count }));
  }, [events.data]);

  const avgScore = useMemo(() => {
    if (!scores.data?.items.length) return null;
    const sum = scores.data.items.reduce((acc, s) => acc + s.score, 0);
    return (sum / scores.data.items.length).toFixed(1);
  }, [scores.data]);

  return (
    <AppShell title="Safety">
      <div className="space-y-6 max-w-7xl mx-auto">
        <h2 className="font-serif text-[22px] text-ink flex items-center gap-2">
          <ShieldAlert size={20} className="text-[#C58783]" />
          Safety Monitoring
        </h2>

        {/* KPI row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {scores.isLoading ? (
            [1, 2, 3, 4].map((i) => <SkeletonCard key={i} />)
          ) : (
            <>
              <div className="col-span-2 lg:col-span-1">
                <KpiCard
                  label="Avg Safety Score"
                  value={avgScore ?? '—'}
                  sub="Across all deliveries"
                  lead
                />
              </div>
              <KpiCard
                label="Open Alerts"
                value={alerts.data?.pagination.total_items ?? '—'}
                sub="Unacknowledged"
              />
              <KpiCard
                label="Safety Events"
                value={events.data?.pagination.total_items ?? '—'}
                sub="All recorded"
              />
              <KpiCard
                label="Deliveries Scored"
                value={scores.data?.pagination.total_items ?? '—'}
              />
            </>
          )}
        </div>

        {/* Live Trips Panel */}
        <div className="card p-5 space-y-3 bg-[#121824] border border-amber-500/30">
          <div className="flex items-center justify-between">
            <h3 className="section-title text-amber-400">Live In-Transit Trips & Simulation</h3>
            {activeDeliveries.data && (
              <span className="caption">{activeDeliveries.data.pagination.total_items} in-transit</span>
            )}
          </div>
          {activeDeliveries.isLoading && <div className="h-16 skeleton rounded-xl" />}
          {activeDeliveries.data?.items.length === 0 && (
            <p className="caption">No in-transit deliveries currently active.</p>
          )}
          {activeDeliveries.data && activeDeliveries.data.items.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {activeDeliveries.data.items.map((d) => (
                <div key={d.id} className="p-3 rounded-xl bg-slate-900/90 border border-slate-800 flex items-center justify-between text-xs">
                  <div>
                    <p className="font-mono font-bold text-white">{d.delivery_code}</p>
                    <p className="text-[11px] text-slate-400">Driver #{d.driver_id} · Vehicle #{d.vehicle_id}</p>
                  </div>
                  <Link
                    to={`/deliveries/${d.id}`}
                    className="px-3 py-1.5 rounded-lg bg-amber-500/20 text-amber-300 hover:bg-amber-500/30 font-medium text-[11px] transition-colors"
                  >
                    Simulate / Track
                  </Link>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Charts + alerts grid */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {/* Event type chart */}
          <div className="card p-5 space-y-3">
            <h3 className="section-title">Events by Type</h3>
            {events.isLoading && <div className="h-48 skeleton rounded" />}
            {events.isError && <ErrorState message="Could not load safety events." />}
            {eventChartData.length === 0 && !events.isLoading && (
              <EmptyState title="No safety events recorded." />
            )}
            {eventChartData.length > 0 && (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={eventChartData} margin={{ left: -20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2D343E" />
                  <XAxis dataKey="type" tick={{ fontSize: 11, fill: '#98A1AD' }} />
                  <YAxis tick={{ fontSize: 11, fill: '#98A1AD' }} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ background: '#1B2027', border: '1px solid #2D343E', borderRadius: 8, fontSize: 12 }}
                    itemStyle={{ color: '#E7EAEE' }}
                    labelStyle={{ color: '#98A1AD' }}
                  />
                  <Bar dataKey="count" fill="#8C4A47" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Safety scores */}
          <div className="card p-5 space-y-3">
            <h3 className="section-title">Driver Safety Scores</h3>
            {scores.isLoading && <SkeletonTable rows={5} />}
            {scores.isError && <ErrorState message="Could not load safety scores." />}
            {scores.data?.items.length === 0 && <EmptyState title="No safety scores recorded." />}
            {scores.data && scores.data.items.length > 0 && (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {scores.data.items.map((s) => (
                  <div key={s.id} className="flex items-center gap-3 card-inset p-3">
                    <div className="flex-1">
                      <p className="text-sm font-medium text-ink">Delivery #{s.delivery_id}</p>
                      <div className="flex gap-2 mt-1 flex-wrap">
                        <span className="caption">Speed: {s.speed_score.toFixed(0)}</span>
                        <span className="caption">Braking: {s.braking_score.toFixed(0)}</span>
                        <span className="caption">Accel: {s.acceleration_score.toFixed(0)}</span>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className={`font-serif text-xl ${s.score >= 80 ? 'text-[#88A594]' : s.score >= 60 ? 'text-[#C0A063]' : 'text-[#C58783]'}`}>
                        {s.score.toFixed(0)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Alerts table */}
        <div className="card p-5 space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <h3 className="section-title">Safety Alerts</h3>
            <label className="flex items-center gap-2 caption cursor-pointer">
              <input
                type="checkbox"
                checked={showAcknowledged}
                onChange={(e) => { setShowAcknowledged(e.target.checked); setAlertPage(1); }}
                className="rounded border-line"
              />
              Show acknowledged
            </label>
          </div>

          {alerts.isLoading && <SkeletonTable rows={6} />}
          {alerts.isError && <ErrorState onRetry={() => alerts.refetch()} />}
          {alerts.data?.items.length === 0 && <EmptyState title="No alerts." description="All clear!" />}
          {alerts.data && alerts.data.items.length > 0 && (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm" role="table">
                  <thead>
                    <tr className="border-b border-line bg-surface-2">
                      <th className="text-left px-3 py-3 caption font-medium">Type</th>
                      <th className="text-left px-3 py-3 caption font-medium">Severity</th>
                      <th className="text-left px-3 py-3 caption font-medium hidden md:table-cell">Message</th>
                      <th className="text-left px-3 py-3 caption font-medium hidden lg:table-cell">Time</th>
                      <th className="px-3 py-3 caption font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {alerts.data.items.map((a) => (
                      <tr key={a.id} className="table-row-hover">
                        <td className="px-3 py-3 font-medium text-ink">{a.alert_type.replace(/_/g, ' ')}</td>
                        <td className="px-3 py-3"><SeverityBadge severity={a.severity} /></td>
                        <td className="px-3 py-3 caption hidden md:table-cell max-w-xs truncate">{a.message}</td>
                        <td className="px-3 py-3 caption hidden lg:table-cell">
                          {new Date(a.created_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                        </td>
                        <td className="px-3 py-3">
                          {a.acknowledged ? (
                            <span className="badge-ok">
                              <CheckCircle size={11} /> Acknowledged
                            </span>
                          ) : (
                            <button
                              onClick={() => ackMutation.mutate(a.id)}
                              disabled={ackMutation.isPending}
                              className="btn-secondary px-2 py-1 text-xs"
                            >
                              Acknowledge
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex items-center justify-between border-t border-line pt-3">
                <span className="caption">{alerts.data.pagination.total_items} total · Page {alertPage} of {alerts.data.pagination.total_pages}</span>
                <div className="flex gap-2">
                  <button onClick={() => setAlertPage((p) => Math.max(1, p - 1))} disabled={!alerts.data.pagination.has_prev} className="btn-secondary px-3 py-1 text-xs">Previous</button>
                  <button onClick={() => setAlertPage((p) => p + 1)} disabled={!alerts.data.pagination.has_next} className="btn-secondary px-3 py-1 text-xs">Next</button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </AppShell>
  );
}
