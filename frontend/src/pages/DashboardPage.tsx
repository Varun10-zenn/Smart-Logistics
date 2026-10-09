
import { useQuery } from '@tanstack/react-query';
import { Truck, ShieldAlert, Zap, Warehouse, Package, Clock } from 'lucide-react';
import { AppShell } from '../components/layout/AppShell';
import { KpiCard } from '../components/ui/KpiCard';
import { SkeletonCard } from '../components/ui/Skeleton';
import { ErrorState, EmptyState } from '../components/ui/States';
import { SeverityBadge, StatusBadge } from '../components/ui/Badge';
import { deliveryApi } from '../api/deliveryApi';
import { safetyApi } from '../api/safetyApi';
import { chargingApi } from '../api/chargingApi';
import { warehouseApi } from '../api/warehouseApi';
import { useAuth } from '../contexts/AuthContext';

import { getRoleCode } from '../types/api';

function formatRelative(dateStr: string) {
  const d = new Date(dateStr);
  const now = Date.now();
  const diff = now - d.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export function DashboardPage() {
  const { user } = useAuth();
  const role = getRoleCode(user?.role);

  const canViewDeliveries = ['admin', 'fleet_manager', 'driver'].includes(role);

  const deliveries = useQuery({
    queryKey: ['deliveries', 'dashboard'],
    queryFn: () => deliveryApi.list({ page: 1, page_size: 1 }),
    staleTime: 30_000,
    enabled: canViewDeliveries,
  });

  const alerts = useQuery({
    queryKey: ['safety', 'alerts', 'dashboard'],
    queryFn: () => safetyApi.listAlerts({ page: 1, page_size: 5, acknowledged: false }),
    staleTime: 30_000,
    enabled: ['admin', 'fleet_manager'].includes(role),
  });

  const stations = useQuery({
    queryKey: ['charging', 'stations', 'dashboard'],
    queryFn: () => chargingApi.listStations({ page: 1, page_size: 1 }),
    staleTime: 30_000,
  });

  const warehouses = useQuery({
    queryKey: ['warehouses', 'dashboard'],
    queryFn: () => warehouseApi.list({ page: 1, page_size: 1 }),
    staleTime: 60_000,
  });

  const totalDeliveries = deliveries.data?.pagination.total_items ?? 0;
  const totalAlerts = alerts.data?.pagination.total_items ?? 0;
  const totalStations = stations.data?.pagination.total_items ?? 0;
  const totalWarehouses = warehouses.data?.pagination.total_items ?? 0;

  return (
    <AppShell title="Dashboard">
      <div className="space-y-6 max-w-7xl mx-auto">
        {/* Page title */}
        <div>
          <h2 className="font-serif text-[22px] text-ink">
            Good {getGreeting()}, {user?.full_name?.split(' ')[0]}
          </h2>
          <p className="caption mt-0.5">Here's your operational overview.</p>
        </div>

        {/* KPI row */}
        <div className="grid grid-cols-2 lg:grid-cols-6 gap-3">
          {deliveries.isLoading ? (
            <>
              <div className="col-span-2">
                <SkeletonCard />
              </div>
              {[1, 2, 3, 4].map((i) => (
                <SkeletonCard key={i} />
              ))}
            </>
          ) : (
            <>
              <div className="col-span-2">
                <KpiCard
                  label="Active Deliveries"
                  value={totalDeliveries}
                  sub="All time total"
                  lead
                  icon={<Truck size={16} />}
                />
              </div>
              <KpiCard
                label="Warehouses"
                value={totalWarehouses}
                icon={<Warehouse size={16} />}
              />
              <KpiCard
                label="Open Alerts"
                value={totalAlerts}
                sub={totalAlerts > 0 ? 'Unacknowledged' : 'All clear'}
                icon={<ShieldAlert size={16} />}
              />
              <KpiCard
                label="Charging Stations"
                value={totalStations}
                icon={<Zap size={16} />}
              />
              <KpiCard
                label="Role"
                value={role.replace('_', ' ')}
                sub="Your access level"
                icon={<Package size={16} />}
              />
            </>
          )}
        </div>

        {/* Bottom grid */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {/* Safety Alerts panel */}
          {['admin', 'fleet_manager'].includes(role) && (
            <div className="card p-5 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="section-title flex items-center gap-2">
                  <ShieldAlert size={16} className="text-[#C58783]" />
                  Safety Alerts
                </h3>
                {alerts.data && (
                  <span className="caption">{alerts.data.pagination.total_items} open</span>
                )}
              </div>

              {alerts.isLoading && (
                <div className="space-y-2">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-12 skeleton rounded" />
                  ))}
                </div>
              )}
              {alerts.isError && (
                <ErrorState message="Could not load safety alerts." onRetry={() => alerts.refetch()} />
              )}
              {alerts.data?.items.length === 0 && (
                <EmptyState title="No open safety alerts" description="All alerts have been acknowledged." />
              )}
              {alerts.data && alerts.data.items.length > 0 && (
                <div className="divide-y divide-line">
                  {alerts.data.items.map((alert) => (
                    <div key={alert.id} className="flex items-start gap-3 py-3 table-row-hover">
                      <SeverityBadge severity={alert.severity} />
                      <div className="flex-1 min-w-0">
                        <p className="body-text text-sm font-medium truncate">{alert.alert_type.replace(/_/g, ' ')}</p>
                        <p className="caption truncate">{alert.message}</p>
                      </div>
                      <span className="caption shrink-0">{formatRelative(alert.created_at)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Recent deliveries */}
          <DeliveryList role={role} />
        </div>
      </div>
    </AppShell>
  );
}

function DeliveryList({ role }: { role: string }) {
  const canViewDeliveries = ['admin', 'fleet_manager', 'driver'].includes(role);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['deliveries', 'recent'],
    queryFn: () => deliveryApi.list({ page: 1, page_size: 8 }),
    staleTime: 30_000,
    enabled: canViewDeliveries,
  });

  return (
    <div className="card p-5 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="section-title flex items-center gap-2">
          <Truck size={16} className="text-[#8FA6BE]" />
          Recent Deliveries
        </h3>
        {data && <span className="caption">{data.pagination.total_items} total</span>}
      </div>

      {!canViewDeliveries && (
        <EmptyState title="Access Restricted" description="Your user role is not authorized to view delivery records." />
      )}
      {canViewDeliveries && isLoading && (
        <div className="space-y-2">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-10 skeleton rounded" />
          ))}
        </div>
      )}
      {canViewDeliveries && isError && <ErrorState message="Could not load deliveries." onRetry={refetch} />}
      {canViewDeliveries && data?.items.length === 0 && <EmptyState title="No deliveries found." />}
      {data && data.items.length > 0 && (
        <div className="divide-y divide-line">
          {data.items.map((d) => (
            <div key={d.id} className="flex items-center gap-3 py-2.5 table-row-hover">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-ink truncate">{d.delivery_code}</p>
                <p className="caption">Driver #{d.driver_id} · Vehicle #{d.vehicle_id}</p>
              </div>
              <StatusBadge status={d.status} />
              <span className="caption shrink-0 hidden sm:block">
                <Clock size={11} className="inline mr-1" />
                {new Date(d.scheduled_dispatch_time).toLocaleDateString()}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return 'morning';
  if (h < 17) return 'afternoon';
  return 'evening';
}
