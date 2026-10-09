import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Zap, Plug, Calendar, Plus, Play, CheckCircle2, BatteryCharging, DollarSign, Store, RefreshCw } from 'lucide-react';
import { Link } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';
import { KpiCard } from '../components/ui/KpiCard';
import { SkeletonCard } from '../components/ui/Skeleton';
import { StatusBadge } from '../components/ui/Badge';
import { chargingApi } from '../api/chargingApi';
import apiClient from '../lib/apiClient';
import type { ChargingStationRead, ChargingConnectorRead, ChargingSlotRead, ChargingReservationRead } from '../types/api';

export function ChargingPage() {
  const [activeTab, setActiveTab] = useState<'stations' | 'batteries' | 'reservations' | 'costs'>('stations');
  const [stationPage] = useState(1);
  const [sessionPage] = useState(1);
  const [showAddStation, setShowAddStation] = useState(false);
  const [selectedStationId, setSelectedStationId] = useState<number | null>(null);
  const [selectedConnectorId, setSelectedConnectorId] = useState<number | null>(null);

  // New Station Form State
  const [stCode, setStCode] = useState('');
  const [stName, setStName] = useState('');
  const [stLat, setStLat] = useState('13.0827');
  const [stLon, setStLon] = useState('80.2707');
  const [stConnectors, setStConnectors] = useState('2');

  // New Connector Form State
  const [connType, setConnType] = useState('CCS2');
  const [connPower, setConnPower] = useState('50.0');

  // Booking Form State
  const [, setBookingSlotId] = useState<number | null>(null);
  const [bookVehicleId] = useState('1');
  const [bookDriverId] = useState('1');

  const qc = useQueryClient();

  const stations = useQuery({
    queryKey: ['charging', 'stations', stationPage],
    queryFn: () => chargingApi.listStations({ page: stationPage, page_size: 10 }),
    staleTime: 10_000,
  });

  const fleetBatteries = useQuery({
    queryKey: ['fleet-batteries'],
    queryFn: () => apiClient.get<any[]>('/api/v1/vehicles/batteries').then((r) => r.data),
    refetchInterval: 5000,
  });

  const sessions = useQuery({
    queryKey: ['charging', 'sessions', sessionPage],
    queryFn: () => chargingApi.listSessions({ page: sessionPage }),
    staleTime: 10_000,
  });

  const reservations = useQuery({
    queryKey: ['charging', 'reservations'],
    queryFn: () => chargingApi.listReservations({ page: 1 }),
    staleTime: 10_000,
  });

  const connectors = useQuery({
    queryKey: ['charging', 'connectors', selectedStationId],
    queryFn: () => chargingApi.listConnectors({ page: 1, station_id: selectedStationId || undefined }),
    staleTime: 10_000,
  });

  const slots = useQuery({
    queryKey: ['charging', 'slots', selectedConnectorId],
    queryFn: () => chargingApi.listSlots({ page: 1, connector_id: selectedConnectorId || undefined }),
    enabled: !!selectedConnectorId,
    staleTime: 10_000,
  });

  const generateDepotMutation = useMutation({
    mutationFn: (whId: number) => apiClient.post(`/api/v1/warehouses/${whId}/charging/generate`, { connectors: 2, max_power_kw: 50.0 }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['charging', 'stations'] });
      alert('Depot chargers generated for store!');
    },
  });

  const createStationMutation = useMutation({
    mutationFn: () =>
      chargingApi.createStation({
        station_code: stCode,
        name: stName,
        latitude: parseFloat(stLat),
        longitude: parseFloat(stLon),
        total_connectors: parseInt(stConnectors, 10),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['charging', 'stations'] });
      setShowAddStation(false);
      setStCode('');
      setStName('');
    },
    onError: (err: any) => {
      alert(err.response?.data?.detail?.message || 'Failed to create station.');
    },
  });

  const createConnectorMutation = useMutation({
    mutationFn: () =>
      chargingApi.createConnector(selectedStationId!, {
        connector_type: connType,
        max_power_kw: parseFloat(connPower),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['charging', 'connectors'] });
    },
    onError: (err: any) => {
      alert(err.response?.data?.detail?.message || 'Failed to add connector.');
    },
  });

  const generateSlotsMutation = useMutation({
    mutationFn: (connectorId: number) => chargingApi.generateSlots(connectorId, { hours_ahead: 24 }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['charging', 'slots'] });
    },
  });

  const createReservationMutation = useMutation({
    mutationFn: (slotId: number) =>
      chargingApi.createReservation({
        slot_id: slotId,
        vehicle_id: parseInt(bookVehicleId, 10),
        driver_id: parseInt(bookDriverId, 10),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['charging', 'reservations'] });
      qc.invalidateQueries({ queryKey: ['charging', 'slots'] });
      setBookingSlotId(null);
    },
    onError: (err: any) => {
      alert(err.response?.data?.detail?.message || 'Failed to book slot.');
    },
  });

  const startSessionMutation = useMutation({
    mutationFn: (resId: number) => chargingApi.startSession(resId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['charging', 'reservations'] });
      qc.invalidateQueries({ queryKey: ['charging', 'sessions'] });
      qc.invalidateQueries({ queryKey: ['fleet-batteries'] });
    },
  });

  const completeSessionMutation = useMutation({
    mutationFn: (resId: number) => chargingApi.completeSession(resId, 90.0),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['charging', 'reservations'] });
      qc.invalidateQueries({ queryKey: ['charging', 'sessions'] });
      qc.invalidateQueries({ queryKey: ['fleet-batteries'] });
    },
  });

  const availableConnectors = connectors.data?.items.filter((c) => c.status === 'available').length ?? 0;
  const totalCostDelivered = sessions.data?.items.reduce((sum: number, s: any) => sum + (s.energy_kwh_delivered * 12.5), 0) || 0;

  return (
    <AppShell title="EV Charging">
      <div className="space-y-6 max-w-7xl mx-auto">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <h2 className="font-serif text-[22px] text-ink flex items-center gap-2">
            <Zap size={20} className="text-[#C0A063]" />
            EV Charging Management
          </h2>
          <div className="flex gap-2">
            <button
              onClick={() => setShowAddStation(!showAddStation)}
              className="btn-secondary flex items-center gap-1.5 text-xs"
            >
              <Plus size={14} /> Add Station
            </button>
            <Link to="/charging/optimize" className="btn-primary flex items-center gap-2 text-sm">
              <Zap size={15} /> Charging Optimizer
            </Link>
          </div>
        </div>

        {/* Add Station Modal / Form */}
        {showAddStation && (
          <div className="card p-5 bg-[#121824] border border-amber-500/30 rounded-2xl space-y-4">
            <h3 className="text-sm font-semibold text-white">Create New Charging Station</h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-5 gap-3 text-xs">
              <input
                type="text"
                placeholder="Code (e.g. ST-ADYAR-01)"
                value={stCode}
                onChange={(e) => setStCode(e.target.value)}
                className="input-field"
              />
              <input
                type="text"
                placeholder="Station Name"
                value={stName}
                onChange={(e) => setStName(e.target.value)}
                className="input-field"
              />
              <input
                type="text"
                placeholder="Latitude"
                value={stLat}
                onChange={(e) => setStLat(e.target.value)}
                className="input-field"
              />
              <input
                type="text"
                placeholder="Longitude"
                value={stLon}
                onChange={(e) => setStLon(e.target.value)}
                className="input-field"
              />
              <input
                type="number"
                placeholder="Connectors"
                value={stConnectors}
                onChange={(e) => setStConnectors(e.target.value)}
                className="input-field"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={() => setShowAddStation(false)} className="btn-ghost text-xs">Cancel</button>
              <button
                onClick={() => createStationMutation.mutate()}
                disabled={createStationMutation.isPending || !stCode || !stName}
                className="btn-primary text-xs"
              >
                Create Station
              </button>
            </div>
          </div>
        )}

        {/* KPIs */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {stations.isLoading ? (
            [1, 2, 3, 4].map((i) => <SkeletonCard key={i} />)
          ) : (
            <>
              <div className="col-span-2 lg:col-span-1">
                <KpiCard
                  label="Charging Stations"
                  value={stations.data?.pagination.total_items ?? '—'}
                  sub="Depot & Public"
                  lead
                />
              </div>
              <KpiCard
                label="Available Connectors"
                value={availableConnectors}
                sub="Online now"
                icon={<Plug size={14} />}
              />
              <KpiCard
                label="EV Fleet Status"
                value={fleetBatteries.data?.length ?? '—'}
                sub="Active EV Scooters"
                icon={<BatteryCharging size={14} />}
              />
              <KpiCard
                label="Est. Charging Cost"
                value={`₹${totalCostDelivered.toFixed(0)}`}
                sub="Energy Delivered"
                icon={<DollarSign size={14} />}
              />
            </>
          )}
        </div>

        {/* Tabs Bar */}
        <div className="flex border-b border-line gap-4 text-xs font-semibold">
          <button
            onClick={() => setActiveTab('stations')}
            className={`pb-2 transition-all cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'stations' ? 'border-b-2 border-amber-400 text-amber-400' : 'text-slate-400 hover:text-white'
            }`}
          >
            <Store size={14} /> Stations & Slots
          </button>
          <button
            onClick={() => setActiveTab('batteries')}
            className={`pb-2 transition-all cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'batteries' ? 'border-b-2 border-amber-400 text-amber-400' : 'text-slate-400 hover:text-white'
            }`}
          >
            <BatteryCharging size={14} /> Fleet Batteries ({fleetBatteries.data?.length || 0})
          </button>
          <button
            onClick={() => setActiveTab('reservations')}
            className={`pb-2 transition-all cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'reservations' ? 'border-b-2 border-amber-400 text-amber-400' : 'text-slate-400 hover:text-white'
            }`}
          >
            <Calendar size={14} /> Reservations & Sessions
          </button>
        </div>

        {/* Tab Content 1: Stations & Connectors */}
        {activeTab === 'stations' && (
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
            {/* Stations Column */}
            <div className="card overflow-hidden">
              <div className="p-4 border-b border-line flex items-center justify-between">
                <h3 className="section-title">Stations</h3>
                {stations.data && <span className="caption">{stations.data.pagination.total_items} total</span>}
              </div>

              {stations.data?.items.map((s: ChargingStationRead) => (
                <div
                  key={s.id}
                  onClick={() => {
                    setSelectedStationId(s.id);
                    setSelectedConnectorId(null);
                  }}
                  className={`p-4 flex items-center gap-3 cursor-pointer border-b border-line transition-all ${
                    selectedStationId === s.id ? 'bg-amber-500/10 border-l-4 border-l-amber-500' : 'hover:bg-slate-900/40'
                  }`}
                >
                  <div className="p-2 rounded-btn bg-[#8A6A34]/10 border border-[#8A6A34]/20">
                    <Zap size={14} className="text-[#C0A063]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-ink text-sm">{s.name}</p>
                    <p className="caption">{s.station_code} · {s.total_connectors} connectors</p>
                  </div>
                  <StatusBadge status={s.status} />
                </div>
              ))}
            </div>

            {/* Connectors & Slot Generator Column */}
            <div className="card overflow-hidden p-4 space-y-4">
              <div className="flex items-center justify-between border-b border-line pb-3">
                <h3 className="section-title">Connectors</h3>
                {selectedStationId && (
                  <span className="caption">Station #{selectedStationId}</span>
                )}
              </div>

              {!selectedStationId ? (
                <p className="caption text-center py-8">Select a station to view & add connectors.</p>
              ) : (
                <div className="space-y-3">
                  {/* Add Connector Form */}
                  <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2 text-xs">
                    <h4 className="font-semibold text-slate-300">Add Connector</h4>
                    <div className="flex gap-2">
                      <select
                        value={connType}
                        onChange={(e) => setConnType(e.target.value)}
                        className="input-field text-xs"
                      >
                        <option value="CCS2">CCS2</option>
                        <option value="Type2">Type2</option>
                        <option value="GB_T">GB/T</option>
                        <option value="CHAdeMO">CHAdeMO</option>
                      </select>
                      <input
                        type="number"
                        placeholder="Power (kW)"
                        value={connPower}
                        onChange={(e) => setConnPower(e.target.value)}
                        className="input-field text-xs w-24"
                      />
                      <button
                        onClick={() => createConnectorMutation.mutate()}
                        disabled={createConnectorMutation.isPending}
                        className="btn-primary text-xs px-3 py-1"
                      >
                        Add
                      </button>
                    </div>
                  </div>

                  {/* Connector List */}
                  {connectors.data?.items.map((c: ChargingConnectorRead) => (
                    <div
                      key={c.id}
                      onClick={() => setSelectedConnectorId(c.id)}
                      className={`p-3 rounded-xl border flex items-center justify-between cursor-pointer transition-all ${
                        selectedConnectorId === c.id ? 'bg-amber-500/10 border-amber-500' : 'bg-slate-900/50 border-slate-800'
                      }`}
                    >
                      <div>
                        <p className="font-medium text-white text-xs">Connector #{c.connector_number} ({c.connector_type})</p>
                        <p className="caption">{c.max_power_kw} kW max power</p>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          generateSlotsMutation.mutate(c.id);
                        }}
                        className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] rounded-lg"
                      >
                        Gen 24h Slots
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Slots & Booking Column */}
            <div className="card overflow-hidden p-4 space-y-4">
              <div className="flex items-center justify-between border-b border-line pb-3">
                <h3 className="section-title">Slots & Booking</h3>
                {selectedConnectorId && <span className="caption">Conn #{selectedConnectorId}</span>}
              </div>

              {!selectedConnectorId ? (
                <p className="caption text-center py-8">Select a connector to view & book available slots.</p>
              ) : (
                <div className="space-y-3">
                  {slots.data?.items.length === 0 && (
                    <p className="caption text-center py-4">No slots generated. Click "Gen 24h Slots".</p>
                  )}

                  <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                    {slots.data?.items.map((s: ChargingSlotRead) => (
                      <div key={s.id} className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-xs flex items-center justify-between">
                        <div>
                          <p className="font-mono text-slate-200">
                            {new Date(s.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} - {new Date(s.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </p>
                          <span className={`text-[10px] uppercase ${s.is_booked ? 'text-red-400 font-bold' : 'text-emerald-400 font-semibold'}`}>
                            {s.is_booked ? 'Booked' : 'Available'}
                          </span>
                        </div>

                        {!s.is_booked && (
                          <button
                            onClick={() => createReservationMutation.mutate(s.id)}
                            disabled={createReservationMutation.isPending}
                            className="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs rounded-lg"
                          >
                            Book
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab Content 2: Fleet Batteries Overview */}
        {activeTab === 'batteries' && (
          <div className="card p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="section-title flex items-center gap-2">
                <BatteryCharging size={16} className="text-amber-400" /> EV Fleet Battery Monitoring
              </h3>
              <button onClick={() => fleetBatteries.refetch()} className="btn-secondary text-xs flex items-center gap-1.5">
                <RefreshCw size={13} /> Refresh
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {fleetBatteries.data?.map((ev: any) => {
                const soc = ev.current_soc_percent;
                const isLow = soc < 25.0;
                return (
                  <div key={ev.vehicle_id} className="p-4 rounded-2xl bg-[#121824] border border-slate-800 space-y-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="font-mono text-xs font-bold text-white block">{ev.registration_number}</span>
                        <span className="text-[11px] text-slate-400">{ev.store_name}</span>
                      </div>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                        ev.status === 'needs_charging' ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'bg-emerald-500/10 text-emerald-400'
                      }`}>
                        {ev.status}
                      </span>
                    </div>

                    {/* Visual Battery Bar */}
                    <div className="space-y-1">
                      <div className="flex justify-between text-xs font-mono">
                        <span className="text-slate-400">SoC Level</span>
                        <span className={`font-bold ${isLow ? 'text-red-400' : 'text-emerald-400'}`}>{soc.toFixed(1)}%</span>
                      </div>
                      <div className="w-full bg-slate-900 rounded-full h-2.5 overflow-hidden border border-slate-800">
                        <div
                          className={`h-full rounded-full transition-all ${
                            isLow ? 'bg-gradient-to-r from-red-500 to-amber-500 animate-pulse' : 'bg-gradient-to-r from-emerald-500 to-teal-400'
                          }`}
                          style={{ width: `${Math.min(100, Math.max(0, soc))}%` }}
                        />
                      </div>
                    </div>

                    <div className="text-[11px] text-slate-400 space-y-1 pt-1 font-mono">
                      <div>Type: {ev.connector_type} ({ev.battery_capacity_kwh} kWh)</div>
                      <div>Est. Time to 90%: <span className="text-white font-semibold">{ev.estimated_time_to_full_mins} mins</span></div>
                    </div>

                    {isLow && (
                      <button
                        onClick={() => generateDepotMutation.mutate(ev.warehouse_id)}
                        className="w-full py-1.5 bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/30 text-xs font-semibold rounded-xl"
                      >
                        Auto-Reserve Depot Slot
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Tab Content 3: Reservations & Sessions Management List */}
        {activeTab === 'reservations' && (
          <div className="card p-5 space-y-4">
            <h3 className="section-title flex items-center gap-2">
              <Calendar size={16} className="text-amber-400" /> Active Reservations & Charging Lifecycle
            </h3>

            {reservations.data?.items.length === 0 ? (
              <p className="caption">No active charging reservations.</p>
            ) : (
              <div className="space-y-3">
                {reservations.data?.items.map((r: ChargingReservationRead) => (
                  <div key={r.id} className="p-4 rounded-2xl bg-[#121824] border border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-white text-xs">{r.reservation_code}</span>
                        <StatusBadge status={r.status} />
                      </div>
                      <p className="text-xs text-slate-300 font-medium">
                        {r.vehicle_code || `Vehicle #${r.vehicle_id}`} · {r.driver_name || `Driver #${r.driver_id}`}
                      </p>
                      <p className="text-[11px] text-slate-400 font-mono">
                        {r.station_name ? `${r.station_name} (${r.connector_code}) · ` : ''}
                        {r.slot_time_range || `${new Date(r.start_time).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}`}
                      </p>
                    </div>

                    <div className="flex gap-2">
                      {r.status === 'confirmed' && (
                        <button
                          onClick={() => startSessionMutation.mutate(r.id)}
                          disabled={startSessionMutation.isPending}
                          className="px-3 py-1.5 bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold rounded-xl flex items-center gap-1.5"
                        >
                          <Play size={13} /> Start Charge
                        </button>
                      )}
                      {r.status === 'active' && (
                        <button
                          onClick={() => completeSessionMutation.mutate(r.id)}
                          disabled={completeSessionMutation.isPending}
                          className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-xl flex items-center gap-1.5"
                        >
                          <CheckCircle2 size={13} /> Complete & Set 90% SoC
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </AppShell>
  );
}

