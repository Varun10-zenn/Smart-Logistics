import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Package,
  Clock,
  ArrowLeft,
  ShoppingBag,
  MapPin,
  Store,
  RefreshCw,
  Check
} from 'lucide-react';
import { shopApi } from '../api/shopApi';
import { RouteMap } from '../components/map/RouteMap';

export function OrderTrackingPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const orderId = id ? parseInt(id, 10) : null;

  // Single Order Query (Auto Refetch every 5s while active)
  const {
    data: singleOrder,
    isLoading: isSingleLoading,
    isError: isSingleError,
    refetch: refetchSingle,
  } = useQuery({
    queryKey: ['customer-order', orderId],
    queryFn: () => shopApi.getOrder(orderId!),
    enabled: !!orderId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data && (data.status === 'delivered' || data.status === 'cancelled')) {
        return false; // Stop polling once terminal state reached
      }
      return 5000; // Poll every 5 seconds while pending/batched/picked/in_transit
    },
  });

  // Orders List Query
  const {
    data: ordersList,
    isLoading: isListLoading,
    refetch: refetchList,
  } = useQuery({
    queryKey: ['customer-orders'],
    queryFn: () => shopApi.listOrders(),
    enabled: !orderId,
    refetchInterval: 5000,
  });

  // Helper for status badge styling
  const renderStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'pending':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-medium border border-amber-500/40 text-amber-400 bg-amber-500/10">Order Placed</span>;
      case 'batched':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-medium border border-sky-500/40 text-sky-400 bg-sky-500/10">Packing / Batched</span>;
      case 'picked':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-medium border border-indigo-500/40 text-indigo-400 bg-indigo-500/10">Items Picked</span>;
      case 'dispatched':
      case 'in_transit':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-medium border border-purple-500/40 text-purple-400 bg-purple-500/10">Out for Delivery</span>;
      case 'delivered':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-medium border border-emerald-500/40 text-emerald-400 bg-emerald-500/10">Delivered</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-medium border border-slate-700 text-slate-400 bg-slate-800">{status}</span>;
    }
  };

  // ─── RENDER SINGLE ORDER DETAIL VIEW ────────────────────────────────────────
  if (orderId) {
    if (isSingleLoading) {
      return (
        <div className="min-h-screen bg-[#0B0F17] flex items-center justify-center text-slate-300">
          <div className="flex items-center gap-3">
            <div className="w-5 h-5 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-xs font-medium">Loading live order status...</span>
          </div>
        </div>
      );
    }

    if (isSingleError || !singleOrder) {
      return (
        <div className="min-h-screen bg-[#0B0F17] p-6 text-slate-100 flex items-center justify-center">
          <div className="card p-8 bg-[#121824] border border-slate-800 rounded-2xl max-w-md w-full text-center space-y-4">
            <h2 className="text-lg font-serif text-white">Order Not Found</h2>
            <p className="text-xs text-slate-400">Unable to retrieve status timeline for Order #{orderId}.</p>
            <button
              onClick={() => navigate('/shop/orders')}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-xl transition-colors cursor-pointer"
            >
              Back to My Orders
            </button>
          </div>
        </div>
      );
    }

    // Default Timeline definition
    const TIMELINE_STEPS = [
      { key: 'pending', label: 'Order Placed', desc: 'Order received and queued for batching' },
      { key: 'batched', label: 'Packing & Batching', desc: 'Auto-batched into warehouse pick route' },
      { key: 'picked', label: 'Picked from Darkstore', desc: 'Items collected from shelf storage' },
      { key: 'out_for_delivery', label: 'Out for Delivery', desc: 'EV courier en route to delivery address' },
      { key: 'delivered', label: 'Delivered', desc: 'Handed over to customer' },
    ];

    /**
     * Mappings of backend Order status values:
     * - 'pending' -> Step 0 (Order Placed)
     * - 'batched' -> Step 1 (Packing & Batching)
     * - 'picking' | 'picked' -> Step 2 (Picked from Darkstore)
     * - 'out_for_delivery' | 'in_transit' | 'dispatched' -> Step 3 (Out for Delivery)
     * - 'delivered' -> Step 4 (Delivered)
     */
    const getStepIndex = (status: string) => {
      const s = (status || '').toLowerCase();
      if (s === 'pending') return 0;
      if (s === 'batched') return 1;
      if (s === 'picking' || s === 'picked') return 2;
      if (s === 'out_for_delivery' || s === 'in_transit' || s === 'dispatched') return 3;
      if (s === 'delivered') return 4;
      return 0;
    };

    const currentStepIndex = getStepIndex(singleOrder.status);

    return (
      <div className="min-h-screen bg-[#0B0F17] text-slate-100 font-sans flex flex-col">
        {/* Header */}
        <header className="sticky top-0 z-30 bg-[#121824]/90 backdrop-blur-md border-b border-slate-800 px-4 py-3 sm:px-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/shop/orders')}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
              title="Back"
            >
              <ArrowLeft size={16} />
            </button>
            <div>
              <h1 className="font-serif text-base font-semibold text-white">Order Status #{singleOrder.order_number}</h1>
              <p className="text-[11px] text-slate-400">Live Auto-Updating Timeline (Polls 5s)</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => refetchSingle()}
              className="px-3 py-1.5 rounded-xl border border-slate-700 bg-slate-800 text-xs text-slate-300 hover:bg-slate-700 hover:text-white flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <RefreshCw size={13} />
              <span>Refresh</span>
            </button>
            <button
              onClick={() => navigate('/shop')}
              className="px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <ShoppingBag size={14} />
              <span>Shop More</span>
            </button>
          </div>
        </header>

        {/* Content */}
        <div className="flex-1 max-w-4xl w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-6">
          
          {/* Order Overview Header Card */}
          <div className="card p-6 bg-[#121824] border border-slate-800 rounded-2xl shadow-xl space-y-4">
            <div className="flex items-center justify-between flex-wrap gap-3 pb-4 border-b border-slate-800">
              <div className="space-y-1">
                <span className="text-[11px] uppercase tracking-wider text-slate-400">Order Reference</span>
                <h2 className="text-xl font-mono font-bold text-white">{singleOrder.order_number}</h2>
              </div>
              <div>{renderStatusBadge(singleOrder.status)}</div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
              <div className="space-y-1">
                <span className="text-slate-400 flex items-center gap-1">
                  <Store size={13} className="text-emerald-400" />
                  <span>Fulfillment Center</span>
                </span>
                <p className="font-medium text-slate-200">{singleOrder.warehouse_name || `Warehouse #${singleOrder.warehouse_id}`}</p>
              </div>

              <div className="space-y-1">
                <span className="text-slate-400 flex items-center gap-1">
                  <Clock size={13} className="text-sky-400" />
                  <span>Promised Delivery</span>
                </span>
                <p className="font-medium text-slate-200">
                  {new Date(singleOrder.promised_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </p>
              </div>

              <div className="space-y-1">
                <span className="text-slate-400 flex items-center gap-1">
                  <MapPin size={13} className="text-purple-400" />
                  <span>Destination Address</span>
                </span>
                <p className="font-medium text-slate-200 truncate">{singleOrder.destination_address}</p>
              </div>
            </div>
          </div>

          {/* Out for Delivery Live Rider Tracking Banner & Map */}
          {(singleOrder.status === 'out_for_delivery' || singleOrder.status === 'in_transit' || singleOrder.delivery_status === 'in_transit') && (
            <div className="card p-5 bg-[#121824] border border-indigo-500/40 rounded-2xl space-y-4 shadow-xl">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-indigo-500/20 text-indigo-400 flex items-center justify-center font-bold">
                    <Package size={18} />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-white">Live Courier Tracking</h4>
                    <p className="text-xs text-slate-400">Order is out for delivery</p>
                  </div>
                </div>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                  IN TRANSIT
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3 rounded-xl bg-slate-900/90 border border-slate-800 text-xs">
                <div>
                  <span className="text-slate-500 text-[11px] block">Rider Name</span>
                  <span className="font-semibold text-slate-200">{singleOrder.rider_first_name || 'Courier'}</span>
                </div>
                <div>
                  <span className="text-slate-500 text-[11px] block">Vehicle</span>
                  <span className="font-semibold text-slate-200">{singleOrder.vehicle_type || 'EV Courier'}</span>
                </div>
                <div>
                  <span className="text-slate-500 text-[11px] block">Estimated Arrival</span>
                  <span className="font-mono font-semibold text-emerald-400">
                    {singleOrder.stop_eta ? new Date(singleOrder.stop_eta).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '15 mins'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 text-[11px] block">Stops Ahead</span>
                  <span className="font-mono font-semibold text-amber-400">
                    {singleOrder.stops_before !== undefined && singleOrder.stops_before !== null ? `${singleOrder.stops_before} stops` : 'Direct Stop'}
                  </span>
                </div>
              </div>

              {/* Real Leaflet Map component with tile fallback */}
              <RouteMap
                routeGeometry={singleOrder.route_geometry}
                destLat={singleOrder.customer_lat}
                destLon={singleOrder.customer_lon}
                destAddress={singleOrder.destination_address}
                riderLat={singleOrder.rider_last_lat}
                riderLon={singleOrder.rider_last_lon}
                riderName={singleOrder.rider_first_name || 'Courier'}
                storeName={singleOrder.warehouse_name || 'Warehouse'}
                height="280px"
              />

              {singleOrder.rider_last_lat !== undefined && singleOrder.rider_last_lat !== null && singleOrder.rider_last_lon !== undefined && singleOrder.rider_last_lon !== null && (
                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-xs flex items-center justify-between">
                  <span className="text-slate-400 font-medium flex items-center gap-1.5">
                    <MapPin size={14} className="text-indigo-400" />
                    <span>Courier Live Position:</span>
                  </span>
                  <span className="font-mono text-indigo-300">
                    Lat, Lon: {singleOrder.rider_last_lat.toFixed(4)}, {singleOrder.rider_last_lon.toFixed(4)}
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Vertical Timeline Stepper */}
          <div className="card p-6 bg-[#121824] border border-slate-800 rounded-2xl shadow-xl space-y-6">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Fulfillment Progress</h3>

            <div className="relative pl-6 space-y-8 before:absolute before:left-3 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
              {TIMELINE_STEPS.map((stepItem, idx) => {
                const isDone = idx <= currentStepIndex;
                const isCurrent = idx === currentStepIndex && singleOrder.status !== 'delivered';

                // Check backend provided timeline step if available
                const backendStep = singleOrder.timeline?.find((t) => t.step.toLowerCase() === stepItem.key);
                const stepTimestamp = backendStep?.timestamp
                  ? new Date(backendStep.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                  : null;

                return (
                  <div key={stepItem.key} className="relative flex items-start gap-4">
                    {/* Circle Node */}
                    <div
                      className={`absolute -left-6 top-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                        isDone
                          ? 'bg-emerald-500 text-white shadow-md shadow-emerald-500/30 ring-4 ring-emerald-500/10'
                          : isCurrent
                          ? 'bg-indigo-600 text-white animate-pulse ring-4 ring-indigo-500/20'
                          : 'bg-slate-900 border border-slate-700 text-slate-500'
                      }`}
                    >
                      {isDone ? <Check size={14} /> : idx + 1}
                    </div>

                    <div className="min-w-0 flex-1 space-y-0.5">
                      <div className="flex items-center justify-between gap-2">
                        <h4
                          className={`text-sm font-medium ${
                            isDone ? 'text-emerald-400' : isCurrent ? 'text-white font-semibold' : 'text-slate-500'
                          }`}
                        >
                          {stepItem.label}
                        </h4>
                        {stepTimestamp && (
                          <span className="text-[11px] font-mono text-slate-400">{stepTimestamp}</span>
                        )}
                      </div>
                      <p className="text-xs text-slate-400">{stepItem.desc}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Items Summary Table */}
          <div className="card p-6 bg-[#121824] border border-slate-800 rounded-2xl shadow-xl space-y-4">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Ordered Items</h3>
            <div className="space-y-2">
              {singleOrder.items.map((item, i) => (
                <div
                  key={i}
                  className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center justify-between text-xs"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-slate-800 text-slate-400">
                      <Package size={16} />
                    </div>
                    <div>
                      <p className="font-medium text-slate-200">{item.product_name || `Product SKU #${item.product_id}`}</p>
                      <p className="text-[11px] text-slate-400">Qty: {item.quantity}</p>
                    </div>
                  </div>
                  {item.unit_price && (
                    <span className="font-mono font-semibold text-emerald-400">
                      ₹{(item.unit_price * item.quantity).toFixed(2)}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>

        </div>
      </div>
    );
  }

  // ─── RENDER CUSTOMER ORDERS LIST VIEW ───────────────────────────────────────
  return (
    <div className="min-h-screen bg-[#0B0F17] text-slate-100 font-sans flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-30 bg-[#121824]/90 backdrop-blur-md border-b border-slate-800 px-4 py-3 sm:px-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-400 flex items-center justify-center text-white shadow-lg shadow-sky-500/20">
            <Clock size={20} />
          </div>
          <div>
            <h1 className="font-serif text-base font-semibold text-white">Order History & Tracking</h1>
            <p className="text-[11px] text-slate-400">Real-time Order Status Monitor</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => refetchList()}
            className="px-3 py-1.5 rounded-xl border border-slate-700 bg-slate-800 text-xs text-slate-300 hover:bg-slate-700 hover:text-white flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <RefreshCw size={13} />
            <span>Refresh List</span>
          </button>
          <button
            onClick={() => navigate('/shop')}
            className="px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <ShoppingBag size={14} />
            <span>Shop Catalog</span>
          </button>
        </div>
      </header>

      <div className="flex-1 max-w-4xl w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-6">
        {isListLoading && (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-24 rounded-2xl bg-[#121824] border border-slate-800 p-4 animate-pulse" />
            ))}
          </div>
        )}

        {ordersList && ordersList.length === 0 && (
          <div className="card p-12 bg-[#121824] border border-slate-800 rounded-2xl text-center space-y-4">
            <div className="w-14 h-14 rounded-full bg-slate-900 text-slate-600 flex items-center justify-center mx-auto">
              <Package size={28} />
            </div>
            <div className="space-y-1">
              <h2 className="text-lg font-serif text-white">No Orders Placed Yet</h2>
              <p className="text-xs text-slate-400 max-w-sm mx-auto">
                You haven't placed any grocery orders yet. Browse the catalog to place your first instant order!
              </p>
            </div>
            <button
              onClick={() => navigate('/shop')}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded-xl transition-colors cursor-pointer"
            >
              Start Shopping
            </button>
          </div>
        )}

        {ordersList && ordersList.length > 0 && (
          <div className="space-y-4">
            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Your Active & Past Orders ({ordersList.length})
            </h2>

            <div className="space-y-3">
              {ordersList.map((order) => (
                <div
                  key={order.id}
                  onClick={() => navigate(`/shop/orders/${order.id}`)}
                  className="card p-4 sm:p-5 bg-[#121824] border border-slate-800 hover:border-slate-700 rounded-2xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 cursor-pointer transition-all hover:bg-slate-900/60 shadow-md"
                >
                  <div className="space-y-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-white text-sm">#{order.order_number}</span>
                      {renderStatusBadge(order.status)}
                    </div>

                    <div className="flex items-center gap-3 text-xs text-slate-400 pt-1">
                      <span className="flex items-center gap-1">
                        <Store size={13} className="text-emerald-400" />
                        <span>{order.warehouse_name || `Warehouse #${order.warehouse_id}`}</span>
                      </span>
                      <span>•</span>
                      <span>{new Date(order.created_at).toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                  </div>

                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      navigate(`/shop/orders/${order.id}`);
                    }}
                    className="px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 flex items-center gap-1.5 self-end sm:self-auto transition-colors"
                  >
                    <span>Track Live</span>
                    <ArrowLeft size={14} className="rotate-180" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
