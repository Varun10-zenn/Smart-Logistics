import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Truck, Filter, ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';
import { SkeletonTable } from '../components/ui/Skeleton';
import { ErrorState, EmptyState } from '../components/ui/States';
import { StatusBadge } from '../components/ui/Badge';
import { deliveryApi } from '../api/deliveryApi';

const STATUSES = ['', 'assigned', 'dispatched', 'in_transit', 'completed', 'failed'];

export function DeliveriesPage() {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState('');

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['deliveries', page, statusFilter],
    queryFn: () => deliveryApi.list({ page, page_size: 15, status: statusFilter || undefined }),
    staleTime: 30_000,
  });

  return (
    <AppShell title="Deliveries">
      <div className="space-y-4 max-w-7xl mx-auto">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <h2 className="font-serif text-[22px] text-ink flex items-center gap-2">
            <Truck size={20} className="text-[#8FA6BE]" />
            Deliveries
          </h2>

          {/* Filter */}
          <div className="flex items-center gap-2">
            <Filter size={14} className="text-ink-mute" />
            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
              className="px-3 py-1.5 rounded-input bg-surface-2 border border-line text-sm text-ink focus:outline-none focus:ring-2 focus:ring-[#8FA6BE]"
              aria-label="Filter by status"
            >
              {STATUSES.map((s) => (
                <option key={s} value={s}>{s ? s.replace(/_/g, ' ') : 'All statuses'}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="card overflow-hidden">
          {isLoading && (
            <div className="p-5">
              <SkeletonTable rows={8} />
            </div>
          )}
          {isError && <div className="p-5"><ErrorState onRetry={refetch} /></div>}
          {data?.items.length === 0 && (
            <div className="p-5"><EmptyState title="No deliveries found." description="Try changing the status filter." /></div>
          )}
          {data && data.items.length > 0 && (
            <>
              {/* Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-sm" role="table">
                  <thead>
                    <tr className="border-b border-line bg-surface-2">
                      <th className="text-left px-4 py-3 caption font-medium">Code</th>
                      <th className="text-left px-4 py-3 caption font-medium">Status</th>
                      <th className="text-left px-4 py-3 caption font-medium hidden md:table-cell">Driver</th>
                      <th className="text-left px-4 py-3 caption font-medium hidden md:table-cell">Vehicle</th>
                      <th className="text-left px-4 py-3 caption font-medium hidden lg:table-cell">Scheduled</th>
                      <th className="text-left px-4 py-3 caption font-medium hidden lg:table-cell">ETA</th>
                      <th className="px-4 py-3" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {data.items.map((d) => (
                      <tr key={d.id} className="table-row-hover">
                        <td className="px-4 py-3 font-medium text-ink">{d.delivery_code}</td>
                        <td className="px-4 py-3"><StatusBadge status={d.status} /></td>
                        <td className="px-4 py-3 caption hidden md:table-cell">#{d.driver_id}</td>
                        <td className="px-4 py-3 caption hidden md:table-cell">#{d.vehicle_id}</td>
                        <td className="px-4 py-3 caption hidden lg:table-cell">
                          {new Date(d.scheduled_dispatch_time).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                        </td>
                        <td className="px-4 py-3 caption hidden lg:table-cell">
                          {d.estimated_eta ? new Date(d.estimated_eta).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' }) : '—'}
                        </td>
                        <td className="px-4 py-3">
                          <Link to={`/deliveries/${d.id}`} className="btn-ghost p-1.5" aria-label={`View delivery ${d.delivery_code}`}>
                            <ChevronRight size={16} />
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="flex items-center justify-between px-4 py-3 border-t border-line">
                <span className="caption">
                  {data.pagination.total_items} deliveries · Page {data.pagination.page} of {data.pagination.total_pages}
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={!data.pagination.has_prev}
                    className="btn-secondary px-3 py-1 text-xs"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setPage((p) => p + 1)}
                    disabled={!data.pagination.has_next}
                    className="btn-secondary px-3 py-1 text-xs"
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </AppShell>
  );
}
