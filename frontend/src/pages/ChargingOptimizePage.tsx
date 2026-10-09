import { useState, type FormEvent } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Zap, ArrowLeft, CheckCircle, AlertTriangle, Clock, MapPin, Battery } from 'lucide-react';
import { Link } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';
import { chargingApi } from '../api/chargingApi';
import type { ChargingRecommendResponse } from '../types/api';

function ScoreBar({ value, max = 1 }: { value: number; max?: number }) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div className="h-1.5 rounded-full bg-surface-2 overflow-hidden">
      <div className="h-full bg-grad-lead rounded-full" style={{ width: `${pct}%` }} />
    </div>
  );
}

export function ChargingOptimizePage() {
  const [vehicleId, setVehicleId] = useState('');
  const [currentSoc, setCurrentSoc] = useState('');
  const [minSoc, setMinSoc] = useState('80');
  const [currentLat, setCurrentLat] = useState('');
  const [currentLon, setCurrentLon] = useState('');
  const [destLat, setDestLat] = useState('');
  const [destLon, setDestLon] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [result, setResult] = useState<ChargingRecommendResponse | null>(null);

  const mutation = useMutation({
    mutationFn: chargingApi.recommend,
    onSuccess: (data) => setResult(data),
  });

  const validate = () => {
    const errs: Record<string, string> = {};
    if (!vehicleId || isNaN(Number(vehicleId))) errs.vehicleId = 'Required integer';
    const soc = Number(currentSoc);
    const minsoc = Number(minSoc);
    if (isNaN(soc) || soc < 0 || soc > 100) errs.currentSoc = 'Must be 0–100';
    if (isNaN(minsoc) || minsoc < 0 || minsoc > 100) errs.minSoc = 'Must be 0–100';
    if (minsoc <= soc) errs.minSoc = 'Target SoC must be higher than current SoC';
    if (!currentLat || isNaN(Number(currentLat))) errs.currentLat = 'Required number';
    if (!currentLon || isNaN(Number(currentLon))) errs.currentLon = 'Required number';
    if (!destLat || isNaN(Number(destLat))) errs.destLat = 'Required number';
    if (!destLon || isNaN(Number(destLon))) errs.destLon = 'Required number';
    return errs;
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const errs = validate();
    setErrors(errs);
    if (Object.keys(errs).length > 0) return;
    setResult(null);
    mutation.mutate({
      vehicle_id: Number(vehicleId),
      current_soc_percent: Number(currentSoc),
      minimum_soc_after_charge: Number(minSoc),
      current_lat: Number(currentLat),
      current_lon: Number(currentLon),
      destination_lat: Number(destLat),
      destination_lon: Number(destLon),
    });
  };

  const apiError = mutation.error as any;
  const apiErrorMsg =
    apiError?.response?.data?.detail?.message ||
    apiError?.response?.data?.error?.message ||
    apiError?.message ||
    'Optimization failed. Check the form values and try again.';

  return (
    <AppShell title="EV Optimizer">
      <div className="max-w-2xl mx-auto space-y-5">
        <Link to="/charging" className="btn-ghost inline-flex items-center gap-1.5 text-sm">
          <ArrowLeft size={15} /> EV Charging
        </Link>

        <div>
          <h2 className="font-serif text-[22px] text-ink flex items-center gap-2">
            <Zap size={20} className="text-[#C0A063]" />
            Multi-Objective Charging Optimizer
          </h2>
          <p className="caption mt-1">
            The backend optimizes station selection based on distance, wait time, and charging duration.
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="card p-5 space-y-4" noValidate>
          <h3 className="section-title">Vehicle & State of Charge</h3>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1 col-span-2 sm:col-span-1">
              <label htmlFor="vehicleId" className="caption font-medium text-ink">Vehicle ID</label>
              <input id="vehicleId" type="number" min={1} value={vehicleId} onChange={(e) => setVehicleId(e.target.value)}
                className="w-full px-3 py-2 rounded-input bg-surface-2 border border-line text-ink text-sm focus:outline-none focus:ring-2 focus:ring-[#8FA6BE]"
                placeholder="e.g. 1" />
              {errors.vehicleId && <p className="caption text-[#C58783]">{errors.vehicleId}</p>}
            </div>

            <div className="space-y-1 col-span-2 sm:col-span-1">
              <label htmlFor="currentSoc" className="caption font-medium text-ink">Current SoC (%)</label>
              <input id="currentSoc" type="number" min={0} max={100} step={0.1} value={currentSoc} onChange={(e) => setCurrentSoc(e.target.value)}
                className="w-full px-3 py-2 rounded-input bg-surface-2 border border-line text-ink text-sm focus:outline-none focus:ring-2 focus:ring-[#8FA6BE]"
                placeholder="e.g. 25" />
              {errors.currentSoc && <p className="caption text-[#C58783]">{errors.currentSoc}</p>}
            </div>

            <div className="space-y-1 col-span-2">
              <label htmlFor="minSoc" className="caption font-medium text-ink">Target SoC after charging (%)</label>
              <input id="minSoc" type="number" min={0} max={100} step={0.1} value={minSoc} onChange={(e) => setMinSoc(e.target.value)}
                className="w-full px-3 py-2 rounded-input bg-surface-2 border border-line text-ink text-sm focus:outline-none focus:ring-2 focus:ring-[#8FA6BE]"
                placeholder="e.g. 80" />
              {errors.minSoc && <p className="caption text-[#C58783]">{errors.minSoc}</p>}
            </div>
          </div>

          <div className="border-t border-line pt-4">
            <h3 className="section-title mb-3">Current & Destination Coordinates</h3>
            <div className="grid grid-cols-2 gap-4">
              {[
                { id: 'currentLat', label: 'Current Latitude', val: currentLat, set: setCurrentLat, err: errors.currentLat, ph: 'e.g. 13.0' },
                { id: 'currentLon', label: 'Current Longitude', val: currentLon, set: setCurrentLon, err: errors.currentLon, ph: 'e.g. 80.0' },
                { id: 'destLat', label: 'Destination Latitude', val: destLat, set: setDestLat, err: errors.destLat, ph: 'e.g. 13.2' },
                { id: 'destLon', label: 'Destination Longitude', val: destLon, set: setDestLon, err: errors.destLon, ph: 'e.g. 80.2' },
              ].map(({ id, label, val, set, err, ph }) => (
                <div key={id} className="space-y-1">
                  <label htmlFor={id} className="caption font-medium text-ink">{label}</label>
                  <input id={id} type="number" step="any" value={val} onChange={(e) => set(e.target.value)}
                    className="w-full px-3 py-2 rounded-input bg-surface-2 border border-line text-ink text-sm focus:outline-none focus:ring-2 focus:ring-[#8FA6BE]"
                    placeholder={ph} />
                  {err && <p className="caption text-[#C58783]">{err}</p>}
                </div>
              ))}
            </div>
          </div>

          {mutation.isError && (
            <div className="flex items-start gap-2 p-3 rounded-input bg-[#8C4A47]/10 border border-[#8C4A47]/30 text-[#C58783] text-sm">
              <AlertTriangle size={15} className="mt-0.5 shrink-0" />
              <span>{apiErrorMsg}</span>
            </div>
          )}

          <button type="submit" disabled={mutation.isPending} className="btn-primary w-full py-2.5 flex items-center justify-center gap-2">
            {mutation.isPending ? (
              <><span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Optimizing...</>
            ) : (
              <><Zap size={15} /> Find Best Charging Station</>
            )}
          </button>
        </form>

        {/* Results */}
        {result && (
          <div className="space-y-4">
            {/* Recommended */}
            <div className="card p-5 space-y-4">
              <div className="flex items-center gap-2">
                <CheckCircle size={18} className="text-[#88A594]" />
                <h3 className="section-title">Recommended Station</h3>
                {result.fallback_used && (
                  <span className="badge-warn">Fallback result</span>
                )}
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="card-inset p-3 text-center">
                  <p className="caption mb-1">Station</p>
                  <p className="kpi-number text-xl">#{result.recommended_station_id}</p>
                </div>
                <div className="card-inset p-3 text-center">
                  <p className="caption mb-1 flex items-center justify-center gap-1"><MapPin size={11} /> Detour</p>
                  <p className="font-serif text-xl text-ink">{result.route_detour_km.toFixed(1)} km</p>
                </div>
                <div className="card-inset p-3 text-center">
                  <p className="caption mb-1 flex items-center justify-center gap-1"><Clock size={11} /> Wait</p>
                  <p className="font-serif text-xl text-ink">{Math.round(result.estimated_wait_minutes)} min</p>
                </div>
                <div className="card-inset p-3 text-center">
                  <p className="caption mb-1 flex items-center justify-center gap-1"><Battery size={11} /> Charge</p>
                  <p className="font-serif text-xl text-ink">{Math.round(result.estimated_charge_minutes)} min</p>
                </div>
              </div>

              <div className="space-y-1">
                <p className="caption">Optimization score (lower is better)</p>
                <ScoreBar value={result.station_score} max={Math.max(result.station_score, ...result.candidate_stations.map((c) => c.station_score), 0.01)} />
                <p className="caption text-[11px]">{result.station_score.toFixed(4)}</p>
              </div>

              {result.optimization_metadata?.energy_required_kwh !== undefined && (
                <div className="card-inset p-3">
                  <p className="caption mb-0.5">Energy required</p>
                  <p className="text-sm text-ink font-medium">{String(result.optimization_metadata.energy_required_kwh)} kWh</p>
                </div>
              )}

              <p className="body-text text-ink-mute text-sm italic">"{result.explanation}"</p>
            </div>

            {/* Alternatives */}
            {result.candidate_stations.length > 1 && (
              <div className="card p-5 space-y-3">
                <h3 className="section-title">All Candidates</h3>
                <div className="space-y-2">
                  {result.candidate_stations.map((c, i) => (
                    <div
                      key={`${c.station_id}-${c.connector_id}`}
                      className={`card-inset p-3 flex items-center gap-4 ${i === 0 ? 'border-[#4F6B5A]/40' : ''}`}
                    >
                      <span className="font-serif text-lg text-ink w-6 text-center">{i + 1}</span>
                      <div className="flex-1 grid grid-cols-4 gap-2 text-xs">
                        <div><p className="caption">Station</p><p className="text-ink font-medium">#{c.station_id}</p></div>
                        <div><p className="caption">Detour</p><p className="text-ink">{c.route_detour_km.toFixed(1)} km</p></div>
                        <div><p className="caption">Wait</p><p className="text-ink">{Math.round(c.estimated_wait_minutes)} min</p></div>
                        <div><p className="caption">Charge</p><p className="text-ink">{Math.round(c.estimated_charge_minutes)} min</p></div>
                      </div>
                      {i === 0 && <span className="badge-ok shrink-0">Recommended</span>}
                    </div>
                  ))}
                </div>
                <p className="caption text-[11px]">Algorithm: {result.algorithm}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </AppShell>
  );
}
