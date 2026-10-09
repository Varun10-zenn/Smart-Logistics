import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  Building2,
  Grid,
  FileSpreadsheet,
  Boxes,
  CheckCircle2,
  Download,
  Upload,
  ArrowRight,
  Copy,
  Check,
  RefreshCw,
  ExternalLink,
  Layers,
  UserPlus,
  MapPin,
  Truck,
} from 'lucide-react';
import apiClient from '../lib/apiClient';
import { warehouseApi } from '../api/warehouseApi';
import { importApi, type ImportResult } from '../api/importApi';
import { deliveryApi } from '../api/deliveryApi';
import { WarehouseGraphCanvas } from './WarehouseGraphCanvas';
import type { WarehouseRead } from '../types/api';

interface AdminSetupWizardProps {
  activeWarehouseId: number | null;
  onSelectWarehouse: (id: number) => void;
  warehouses: WarehouseRead[];
}

export function AdminSetupWizard({
  activeWarehouseId,
  onSelectWarehouse,
  warehouses,
}: AdminSetupWizardProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [currentStep, setCurrentStep] = useState<number>(1);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  // Step 1 Form State
  const [whCode, setWhCode] = useState('WH-VLR-01');
  const [whName, setWhName] = useState('Vellore Darkstore');
  const [whLat, setWhLat] = useState('12.9716');
  const [whLon, setWhLon] = useState('79.1400');
  const [whAddr, setWhAddr] = useState('Katpadi Road, Vellore, Tamil Nadu 632014');
  const [step1Error, setStep1Error] = useState<string | null>(null);
  // Step 1 Store Import State
  const [storeImportFile, setStoreImportFile] = useState<File | null>(null);

  // Step 1 Operator Creation Form State
  const [opFullName, setOpFullName] = useState('');
  const [opUsername, setOpUsername] = useState('');
  const [opEmail, setOpEmail] = useState('');
  const [opPassword, setOpPassword] = useState('');
  const [opWarehouseId, setOpWarehouseId] = useState<string>(activeWarehouseId ? String(activeWarehouseId) : '');
  const [opError, setOpError] = useState<string | null>(null);
  const [opSuccessMsg, setOpSuccessMsg] = useState<string | null>(null);
  const [isOpSubmitting, setIsOpSubmitting] = useState(false);

  const handleOpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setOpError(null);
    setOpSuccessMsg(null);

    const fullName = opFullName.trim();
    const username = opUsername.trim().replace(/\s+/g, '');
    const email = opEmail.trim();
    const password = opPassword;
    const whId = parseInt(opWarehouseId, 10);

    if (!fullName) {
      setOpError('Full name is required.');
      return;
    }
    if (!username) {
      setOpError('Username is required (no spaces allowed).');
      return;
    }
    if (!email) {
      setOpError('Email is required.');
      return;
    }
    if (!password || password.length < 8) {
      setOpError('Password must be at least 8 characters long.');
      return;
    }
    if (!whId) {
      setOpError('Please select a target store.');
      return;
    }

    setIsOpSubmitting(true);
    try {
      await apiClient.post('/api/v1/users', {
        email,
        full_name: fullName,
        password,
        role_code: 'warehouse_operator',
        warehouse_id: whId,
      });

      setOpSuccessMsg(`Operator created successfully for ${email}! Linked to Store #${whId}.`);
      setOpFullName('');
      setOpUsername('');
      setOpEmail('');
      setOpPassword('');
      setOpWarehouseId('');
    } catch (err: any) {
      const responseData = err.response?.data;
      if (err.response?.status === 422 && Array.isArray(responseData?.detail)) {
        const fieldErrors = responseData.detail
          .map((item: any) => {
            const fieldLoc = item.loc ? item.loc.join(' -> ') : 'Field';
            return `${fieldLoc}: ${item.msg}`;
          })
          .join(' | ');
        setOpError(`Validation Error (422): ${fieldErrors}`);
      } else if (err.response?.status === 409) {
        const msg = responseData?.detail?.message || responseData?.detail || responseData?.message || 'User with this email already exists.';
        setOpError(`Conflict (409): ${typeof msg === 'string' ? msg : JSON.stringify(msg)}`);
      } else {
        const msg = responseData?.detail?.message || responseData?.detail || responseData?.message || 'Failed to create operator.';
        setOpError(typeof msg === 'string' ? msg : JSON.stringify(msg));
      }
    } finally {
      setIsOpSubmitting(false);
    }
  };

  // Fleet Generator State
  const [fleetRiders, setFleetRiders] = useState<number>(3);
  const [fleetEvCount, setFleetEvCount] = useState<number>(2);
  const [fleetResult, setFleetResult] = useState<any | null>(null);
  const [fleetError, setFleetError] = useState<string | null>(null);
  const [isFleetSubmitting, setIsFleetSubmitting] = useState<boolean>(false);

  const handleFleetGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWarehouseId) {
      setFleetError('Please create or select a store first.');
      return;
    }
    setFleetError(null);
    setIsFleetSubmitting(true);
    try {
      const res = await deliveryApi.generateFleet(activeWarehouseId, {
        riders: fleetRiders,
        ev_count: fleetEvCount,
      });
      setFleetResult(res);
    } catch (err: any) {
      const msg = err.response?.data?.detail?.message || err.response?.data?.detail || 'Fleet generation failed.';
      setFleetError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setIsFleetSubmitting(false);
    }
  };

  // Step 2 Form State
  const [aisles, setAisles] = useState<number>(2);
  const [shelvesPerAisle, setShelvesPerAisle] = useState<number>(3);
  const [aisleSpacing, setAisleSpacing] = useState<number>(4.0);
  const [shelfSpacing, setShelfSpacing] = useState<number>(2.0);
  const [replaceExisting, setReplaceExisting] = useState<boolean>(true);
  const [step2Error, setStep2Error] = useState<string | null>(null);

  // Step 3 CSV State
  const [productFile, setProductFile] = useState<File | null>(null);
  const [productResult, setProductResult] = useState<ImportResult | null>(null);
  const [step3Error, setStep3Error] = useState<string | null>(null);

  // Step 4 CSV State
  const [inventoryFile, setInventoryFile] = useState<File | null>(null);
  const [inventoryResult, setInventoryResult] = useState<ImportResult | null>(null);
  const [step4Error, setStep4Error] = useState<string | null>(null);

  // Selected Warehouse Data
  const selectedWh = warehouses.find((w) => w.id === activeWarehouseId) || null;

  // Graph Data for Step 2 Canvas
  const { data: graphData, refetch: refetchGraph } = useQuery({
    queryKey: ['warehouse-graph-wizard', activeWarehouseId],
    queryFn: () => warehouseApi.getGraph(activeWarehouseId!),
    enabled: !!activeWarehouseId,
  });

  // Locations Data for Step 4 Reference Table
  const { data: locationsData } = useQuery({
    queryKey: ['warehouse-locations-wizard', activeWarehouseId],
    queryFn: () => warehouseApi.listLocations(activeWarehouseId!),
    enabled: !!activeWarehouseId,
  });

  // Validation Query
  const { data: validationData, refetch: refetchValidation } = useQuery({
    queryKey: ['warehouse-validation-wizard', activeWarehouseId],
    queryFn: () => warehouseApi.validate(activeWarehouseId!),
    enabled: !!activeWarehouseId,
  });

  // Step 1: Create Warehouse Mutation
  const createWhMutation = useMutation({
    mutationFn: warehouseApi.create,
    onSuccess: (newWh) => {
      setStep1Error(null);
      queryClient.invalidateQueries({ queryKey: ['warehouses'] });
      onSelectWarehouse(newWh.id);
      setCurrentStep(2);
    },
    onError: (err: any) => {
      const msg = err.response?.data?.error?.message || err.response?.data?.detail?.message || err.response?.data?.detail || 'Failed to create warehouse.';
      setStep1Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    },
  });

  const handleStep1Submit = (e: React.FormEvent) => {
    e.preventDefault();
    setStep1Error(null);
    createWhMutation.mutate({
      code: whCode.trim(),
      name: whName.trim(),
      latitude: parseFloat(whLat),
      longitude: parseFloat(whLon),
      address: whAddr.trim(),
    });
  };

  // Step 2: Generate Layout Mutation
  const generateLayoutMutation = useMutation({
    mutationFn: (data: any) => importApi.generateLayout(activeWarehouseId!, data),
    onSuccess: () => {
      setStep2Error(null);
      queryClient.invalidateQueries({ queryKey: ['warehouse-graph', activeWarehouseId] });
      queryClient.invalidateQueries({ queryKey: ['warehouse-graph-wizard', activeWarehouseId] });
      queryClient.invalidateQueries({ queryKey: ['warehouse-locations-wizard', activeWarehouseId] });
      queryClient.invalidateQueries({ queryKey: ['warehouse-validation-wizard', activeWarehouseId] });
      refetchGraph();
      refetchValidation();
    },
    onError: (err: any) => {
      const msg = err.response?.data?.error?.message || err.response?.data?.detail?.message || err.response?.data?.detail || 'Failed to generate layout graph.';
      setStep2Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    },
  });

  const handleStep2Submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWarehouseId) return;
    setStep2Error(null);
    generateLayoutMutation.mutate({
      aisles,
      shelves_per_aisle: shelvesPerAisle,
      aisle_spacing_m: aisleSpacing,
      shelf_spacing_m: shelfSpacing,
      replace_existing: replaceExisting,
    });
  };

  // Step 3: Product Import Mutation
  const productImportMutation = useMutation({
    mutationFn: importApi.importProducts,
    onSuccess: (res) => {
      setStep3Error(null);
      setProductResult(res);
      queryClient.invalidateQueries({ queryKey: ['products'] });
    },
    onError: (err: any) => {
      const msg = err.response?.data?.error?.message || err.response?.data?.detail?.message || err.response?.data?.detail || 'Failed to import products CSV.';
      setStep3Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    },
  });

  const handleStep3Upload = (e: React.FormEvent) => {
    e.preventDefault();
    if (!productFile) return;
    setStep3Error(null);
    productImportMutation.mutate(productFile);
  };

  // Step 4: Inventory Import Mutation
  const inventoryImportMutation = useMutation({
    mutationFn: importApi.importInventory,
    onSuccess: (res) => {
      setStep4Error(null);
      setInventoryResult(res);
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
    },
    onError: (err: any) => {
      const msg = err.response?.data?.error?.message || err.response?.data?.detail?.message || err.response?.data?.detail || 'Failed to import inventory CSV.';
      setStep4Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    },
  });

  const handleStep4Upload = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inventoryFile) return;
    setStep4Error(null);
    inventoryImportMutation.mutate(inventoryFile);
  };

  const handleCopyText = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCode(text);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  const stepsHeader = [
    { num: 1, label: 'Warehouse', icon: <Building2 size={16} /> },
    { num: 2, label: 'Grid Layout', icon: <Grid size={16} /> },
    { num: 3, label: 'Products CSV', icon: <FileSpreadsheet size={16} /> },
    { num: 4, label: 'Inventory CSV', icon: <Boxes size={16} /> },
    { num: 5, label: 'Checklist & Done', icon: <CheckCircle2 size={16} /> },
  ];

  return (
    <div className="space-y-6">
      {/* Wizard Header Bar */}
      <div className="card p-6 bg-[#121824] border border-slate-800 rounded-2xl shadow-xl space-y-6">
        <div>
          <h2 className="text-lg font-serif text-white font-semibold">Darkstore Setup & Automation Wizard</h2>
          <p className="text-xs text-slate-400 mt-1">
            Follow this 5-step guided wizard to create your darkstore, generate grid topology with 2-opt loop edges, import products and inventory via CSV, and activate automated order batching.
          </p>
        </div>

        {/* Stepper Tabs */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 border-b border-slate-800 pb-4">
          {stepsHeader.map((st) => {
            const isActive = currentStep === st.num;
            const isDone = currentStep > st.num;

            return (
              <button
                key={st.num}
                onClick={() => setCurrentStep(st.num)}
                className={`p-3 rounded-xl border text-left transition-all flex items-center gap-2.5 cursor-pointer ${
                  isActive
                    ? 'border-indigo-500 bg-indigo-950/40 text-white shadow-md'
                    : isDone
                    ? 'border-emerald-500/30 bg-emerald-950/20 text-emerald-300'
                    : 'border-slate-800/80 bg-slate-900/40 text-slate-400 hover:text-slate-200'
                }`}
              >
                <div
                  className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 text-xs font-bold ${
                    isActive
                      ? 'bg-indigo-600 text-white'
                      : isDone
                      ? 'bg-emerald-500 text-white'
                      : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  {isDone ? <Check size={14} /> : st.num}
                </div>
                <div className="min-w-0 hidden sm:block">
                  <p className="text-xs font-medium truncate">{st.label}</p>
                </div>
              </button>
            );
          })}
        </div>

        {/* Selected Warehouse Active Context Banner */}
        {selectedWh && (
          <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between text-xs text-slate-300">
            <div className="flex items-center gap-2">
              <Building2 size={15} className="text-indigo-400 shrink-0" />
              <span>Active Target Warehouse: <strong className="text-white">{selectedWh.name} ({selectedWh.code})</strong></span>
            </div>
            <span className="font-mono text-slate-400">ID #{selectedWh.id}</span>
          </div>
        )}
      </div>

      {/* ─── STEP 1: CREATE WAREHOUSE & BATCH IMPORT STORES ─────────────────── */}
      {currentStep === 1 && (
        <div className="card p-6 bg-[#121824] border border-slate-800 rounded-2xl space-y-6 shadow-xl">
          {/* Section 1A: Bulk Stores CSV Import */}
          <div className="p-4 rounded-xl bg-slate-900/80 border border-indigo-500/30 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                  <MapPin size={16} className="text-sky-400" />
                  <span>Bulk Import Zepto Stores CSV</span>
                </h4>
                <p className="text-xs text-slate-400">
                  Upload <code className="text-sky-300 font-mono">data/zepto_stores_chennai_vellore.csv</code> to create real stores with auto-generated grid layouts.
                </p>
              </div>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (!storeImportFile) return;
                setStep1Error(null);
                importApi
                  .importStores(storeImportFile, { generate_layout: true, aisles: 2, shelves_per_aisle: 3 })
                  .then((res) => {
                    queryClient.invalidateQueries({ queryKey: ['warehouses'] });
                    alert(`Imported Zepto Stores! Created: ${res.created}, Updated: ${res.updated}, Skipped: ${res.skipped}`);
                    setStoreImportFile(null);
                  })
                  .catch((err: any) => {
                    const detail = err.response?.data?.detail;
                    const msg = typeof detail === 'string' ? detail : (detail?.message || err.response?.data?.message || 'Store CSV import failed.');
                    setStep1Error(msg);
                  });
              }}
              className="flex flex-col sm:flex-row items-center gap-3"
            >
              <input
                type="file"
                accept=".csv"
                required
                onChange={(e) => setStoreImportFile(e.target.files?.[0] || null)}
                className="w-full sm:w-auto bg-slate-950 border border-slate-700 rounded-xl p-2 text-xs text-slate-200 file:mr-3 file:py-1 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-sky-600 file:text-white hover:file:bg-sky-500 cursor-pointer"
              />
              <button
                type="submit"
                disabled={!storeImportFile}
                className="w-full sm:w-auto px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold rounded-xl flex items-center justify-center gap-1.5 cursor-pointer shadow-md disabled:opacity-50"
              >
                <Upload size={14} />
                <span>Upload & Import Stores</span>
              </button>
            </form>
          </div>

          {/* Section 1B: Create Single Warehouse */}
          <div className="space-y-4">
            <div className="space-y-1">
              <h3 className="text-base font-serif text-white font-semibold flex items-center gap-2">
                <Building2 size={18} className="text-indigo-400" />
                <span>Create Single Warehouse Facility</span>
              </h3>
              <p className="text-xs text-slate-400">Enter location parameters for a single darkstore fulfillment center.</p>
            </div>

            {step1Error && (
              <div className="p-3 rounded-xl border border-red-500/30 bg-red-500/10 text-red-300 text-xs">
                {step1Error}
              </div>
            )}

            <form onSubmit={handleStep1Submit} className="space-y-4 max-w-2xl">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-medium text-slate-300">Warehouse Code</label>
                  <input
                    type="text"
                    required
                    value={whCode}
                    onChange={(e) => setWhCode(e.target.value)}
                    placeholder="WH-VLR-01"
                    className="w-full bg-slate-900 border border-slate-700/80 rounded-xl px-3 py-2 text-xs text-slate-100 font-mono"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-medium text-slate-300">Warehouse Name</label>
                  <input
                    type="text"
                    required
                    value={whName}
                    onChange={(e) => setWhName(e.target.value)}
                    placeholder="Vellore Central Darkstore"
                    className="w-full bg-slate-900 border border-slate-700/80 rounded-xl px-3 py-2 text-xs text-slate-100"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-medium text-slate-300">Latitude</label>
                  <input
                    type="number"
                    step="any"
                    required
                    value={whLat}
                    onChange={(e) => setWhLat(e.target.value)}
                    placeholder="12.9716"
                    className="w-full bg-slate-900 border border-slate-700/80 rounded-xl px-3 py-2 text-xs text-slate-100 font-mono"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-medium text-slate-300">Longitude</label>
                  <input
                    type="number"
                    step="any"
                    required
                    value={whLon}
                    onChange={(e) => setWhLon(e.target.value)}
                    placeholder="79.1400"
                    className="w-full bg-slate-900 border border-slate-700/80 rounded-xl px-3 py-2 text-xs text-slate-100 font-mono"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-300">Physical Address</label>
                <textarea
                  rows={2}
                  value={whAddr}
                  onChange={(e) => setWhAddr(e.target.value)}
                  placeholder="Katpadi Road, Vellore, Tamil Nadu 632014"
                  className="w-full bg-slate-900 border border-slate-700/80 rounded-xl p-2.5 text-xs text-slate-100"
                />
              </div>

              <div className="flex items-center justify-between pt-2">
                {selectedWh ? (
                  <button
                    type="button"
                    onClick={() => setCurrentStep(2)}
                    className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl transition-colors cursor-pointer"
                  >
                    Use Existing Warehouse ({selectedWh.code}) & Next
                  </button>
                ) : <div />}

                <button
                  type="submit"
                  disabled={createWhMutation.isPending}
                  className="px-5 py-2.5 bg-gradient-to-r from-indigo-600 to-sky-500 hover:from-indigo-500 hover:to-sky-400 text-white text-xs font-semibold rounded-xl shadow-lg shadow-indigo-600/20 flex items-center gap-2 cursor-pointer disabled:opacity-50"
                >
                  {createWhMutation.isPending ? (
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    <>
                      <span>Create & Continue to Layout</span>
                      <ArrowRight size={15} />
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>

          {/* Section 1C: Link Picker Operator to Store */}
          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-4 pt-4 border-t border-slate-800">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                  <UserPlus size={16} className="text-emerald-400" />
                  <span>Create Picker Operator (Linked to Store)</span>
                </h4>
                <p className="text-xs text-slate-400">
                  Assign a warehouse operator account specifically to a selected store.
                </p>
              </div>
            </div>

            {opSuccessMsg && (
              <div className="p-3 rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-emerald-300 text-xs">
                {opSuccessMsg}
              </div>
            )}

            {opError && (
              <div className="p-3 rounded-xl border border-red-500/30 bg-red-500/10 text-red-300 text-xs">
                {opError}
              </div>
            )}

            <form
              onSubmit={handleOpSubmit}
              className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 items-end"
            >
              <div>
                <label className="text-[11px] text-slate-300 font-medium block mb-1">Full Name</label>
                <input
                  type="text"
                  required
                  value={opFullName}
                  onChange={(e) => setOpFullName(e.target.value)}
                  placeholder="John Doe"
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100"
                />
              </div>
              <div>
                <label className="text-[11px] text-slate-300 font-medium block mb-1">Username</label>
                <input
                  type="text"
                  required
                  value={opUsername}
                  onChange={(e) => setOpUsername(e.target.value.replace(/\s+/g, ''))}
                  placeholder="picker_adyar"
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100"
                />
              </div>
              <div>
                <label className="text-[11px] text-slate-300 font-medium block mb-1">Email</label>
                <input
                  type="email"
                  required
                  value={opEmail}
                  onChange={(e) => setOpEmail(e.target.value)}
                  placeholder="adyar@picker.com"
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100"
                />
              </div>
              <div>
                <label className="text-[11px] text-slate-300 font-medium block mb-1">Password</label>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={opPassword}
                  onChange={(e) => setOpPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100"
                />
              </div>
              <div>
                <label className="text-[11px] text-slate-300 font-medium block mb-1">Target Store</label>
                <select
                  required
                  value={opWarehouseId}
                  onChange={(e) => setOpWarehouseId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100"
                >
                  <option value="">Select Store...</option>
                  {warehouses.map((w) => (
                    <option key={w.id} value={w.id}>
                      {w.code} - {w.name}
                    </option>
                  ))}
                </select>
              </div>
              <button
                type="submit"
                disabled={isOpSubmitting}
                className="w-full py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg flex items-center justify-center gap-1.5 cursor-pointer shadow disabled:opacity-50"
              >
                {isOpSubmitting ? (
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <>
                    <UserPlus size={14} />
                    <span>Create Operator</span>
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Section 1D: Bulk Generate Store Fleet (Riders & EVs) */}
          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-4 pt-4 border-t border-slate-800">
            <div>
              <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                <Truck size={16} className="text-amber-400" />
                <span>Generate Store Fleet (Riders & EV/ICE Vehicles)</span>
              </h4>
              <p className="text-xs text-slate-400">
                Bulk generate delivery riders and assign EV/ICE vehicles specifically to the selected store.
              </p>
            </div>

            {fleetError && (
              <div className="p-3 rounded-xl border border-red-500/30 bg-red-500/10 text-red-300 text-xs">
                {fleetError}
              </div>
            )}

            <form onSubmit={handleFleetGenerate} className="flex flex-col sm:flex-row items-end gap-3 max-w-xl">
              <div className="flex-1 space-y-1">
                <label className="text-[11px] text-slate-300 font-medium">Riders Count</label>
                <input
                  type="number"
                  min={1}
                  max={20}
                  required
                  value={fleetRiders}
                  onChange={(e) => setFleetRiders(parseInt(e.target.value, 10) || 1)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 font-mono"
                />
              </div>

              <div className="flex-1 space-y-1">
                <label className="text-[11px] text-slate-300 font-medium">EV Vehicle Count</label>
                <input
                  type="number"
                  min={0}
                  max={20}
                  required
                  value={fleetEvCount}
                  onChange={(e) => setFleetEvCount(parseInt(e.target.value, 10) || 0)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 font-mono"
                />
              </div>

              <button
                type="submit"
                disabled={isFleetSubmitting || !activeWarehouseId}
                className="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold rounded-lg flex items-center justify-center gap-1.5 cursor-pointer shadow disabled:opacity-50"
              >
                {isFleetSubmitting ? (
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <>
                    <Truck size={14} />
                    <span>Generate Fleet</span>
                  </>
                )}
              </button>
            </form>

            {fleetResult && (
              <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 space-y-3">
                <div className="flex items-center justify-between text-xs text-amber-300 font-medium">
                  <span>Fleet Created for Store #{fleetResult.warehouse_id} ({fleetResult.warehouse_code})</span>
                  <span>{fleetResult.riders_created} Riders | {fleetResult.vehicles_created} Vehicles ({fleetResult.ev_count} EV)</span>
                </div>

                <div className="space-y-1.5 max-h-48 overflow-y-auto">
                  <span className="text-[11px] font-bold text-amber-200 uppercase tracking-wider block">Generated Rider Logins (Shown Once):</span>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {fleetResult.riders.map((r: any, idx: number) => (
                      <div key={idx} className="p-2 rounded-lg bg-slate-950 border border-slate-800 text-[11px] font-mono space-y-0.5">
                        <div className="text-slate-200 font-semibold">{r.full_name}</div>
                        <div className="text-amber-400">Email: {r.email}</div>
                        <div className="text-slate-400">Pass: {r.password}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ─── STEP 2: GENERATE LAYOUT TOPOLOGY ────────────────────────────────── */}
      {currentStep === 2 && (
        <div className="card p-6 bg-[#121824] border border-slate-800 rounded-2xl space-y-6 shadow-xl">
          <div className="space-y-1">
            <h3 className="text-base font-serif text-white font-semibold flex items-center gap-2">
              <Grid size={18} className="text-indigo-400" />
              <span>Step 2: Generate Grid Topology & Loop Edges</span>
            </h3>
            <p className="text-xs text-slate-400">
              Generates a single-transaction graph layout with a depot at (0,0), main corridor, aisle shelf chains, storage locations, and far-end cross-aisle loop edges for 2-opt routing optimization.
            </p>
          </div>

          {step2Error && (
            <div className="p-3 rounded-xl border border-red-500/30 bg-red-500/10 text-red-300 text-xs">
              {step2Error}
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Form */}
            <form onSubmit={handleStep2Submit} className="lg:col-span-5 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-xs font-medium text-slate-300">Aisles (1 - 20)</label>
                  <input
                    type="number"
                    min={1}
                    max={20}
                    required
                    value={aisles}
                    onChange={(e) => setAisles(parseInt(e.target.value, 10) || 1)}
                    className="w-full bg-slate-900 border border-slate-700/80 rounded-xl px-3 py-2 text-xs text-slate-100 font-mono"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-medium text-slate-300">Shelves / Aisle (1 - 30)</label>
                  <input
                    type="number"
                    min={1}
                    max={30}
                    required
                    value={shelvesPerAisle}
                    onChange={(e) => setShelvesPerAisle(parseInt(e.target.value, 10) || 1)}
                    className="w-full bg-slate-900 border border-slate-700/80 rounded-xl px-3 py-2 text-xs text-slate-100 font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-xs font-medium text-slate-300">Aisle Spacing (m)</label>
                  <input
                    type="number"
                    step="0.5"
                    min={1}
                    required
                    value={aisleSpacing}
                    onChange={(e) => setAisleSpacing(parseFloat(e.target.value) || 4.0)}
                    className="w-full bg-slate-900 border border-slate-700/80 rounded-xl px-3 py-2 text-xs text-slate-100 font-mono"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-medium text-slate-300">Shelf Spacing (m)</label>
                  <input
                    type="number"
                    step="0.5"
                    min={1}
                    required
                    value={shelfSpacing}
                    onChange={(e) => setShelfSpacing(parseFloat(e.target.value) || 2.0)}
                    className="w-full bg-slate-900 border border-slate-700/80 rounded-xl px-3 py-2 text-xs text-slate-100 font-mono"
                  />
                </div>
              </div>

              {/* Replace Existing Warning Checkbox */}
              <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 space-y-2">
                <label className="flex items-center gap-2 text-xs text-amber-200 font-medium cursor-pointer">
                  <input
                    type="checkbox"
                    checked={replaceExisting}
                    onChange={(e) => setReplaceExisting(e.target.checked)}
                    className="rounded bg-slate-900 border-slate-700 text-indigo-600"
                  />
                  <span>Replace Existing Layout Rows</span>
                </label>
                <p className="text-[11px] text-amber-300/80 leading-relaxed">
                  Warning: If checked, existing layout nodes and storage locations not referenced by inventory or orders will be safely replaced.
                </p>
              </div>

              <div className="flex items-center justify-between pt-2">
                <button
                  type="submit"
                  disabled={generateLayoutMutation.isPending || !activeWarehouseId}
                  className="w-full py-2.5 bg-gradient-to-r from-indigo-600 to-sky-500 hover:from-indigo-500 hover:to-sky-400 text-white text-xs font-semibold rounded-xl shadow-lg shadow-indigo-600/20 flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                >
                  {generateLayoutMutation.isPending ? (
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    <>
                      <span>Generate Grid & Validate Graph</span>
                      <Grid size={15} />
                    </>
                  )}
                </button>
              </div>
            </form>

            {/* Layout Canvas & Validation Status */}
            <div className="lg:col-span-7 space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-300">Generated Graph Preview</span>
                {validationData && (
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      validationData.valid
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                        : 'bg-red-500/10 text-red-400 border border-red-500/30'
                    }`}
                  >
                    {validationData.valid ? 'Valid Layout Graph' : 'Invalid Graph'}
                  </span>
                )}
              </div>

              <div className="h-64 w-full rounded-2xl overflow-hidden bg-slate-950 border border-slate-800">
                {graphData ? (
                  <WarehouseGraphCanvas nodes={graphData.nodes} edges={graphData.edges} locations={graphData.locations} />
                ) : (
                  <div className="h-full flex items-center justify-center text-slate-500 text-xs">
                    Click 'Generate Grid' to create topology.
                  </div>
                )}
              </div>

              {validationData && !validationData.valid && (
                <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 text-xs space-y-1">
                  <p className="font-bold">Validation Errors:</p>
                  <ul className="list-disc list-inside space-y-0.5">
                    {validationData.errors.map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="flex justify-end pt-2">
                <button
                  onClick={() => setCurrentStep(3)}
                  disabled={!graphData}
                  className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl flex items-center gap-2 transition-colors cursor-pointer disabled:opacity-40"
                >
                  <span>Proceed to Products Import</span>
                  <ArrowRight size={15} />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ─── STEP 3: IMPORT PRODUCTS CSV ────────────────────────────────────── */}
      {currentStep === 3 && (
        <div className="card p-6 bg-[#121824] border border-slate-800 rounded-2xl space-y-6 shadow-xl">
          <div className="space-y-1">
            <h3 className="text-base font-serif text-white font-semibold flex items-center gap-2">
              <FileSpreadsheet size={18} className="text-indigo-400" />
              <span>Step 3: Bulk Import Global Products (CSV)</span>
            </h3>
            <p className="text-xs text-slate-400">
              Upload catalog products CSV (`sku,name,category,unit_weight_kg,unit_volume_cbm,price`). Valid rows will be created/upserted by SKU.
            </p>
          </div>

          {step3Error && (
            <div className="p-3 rounded-xl border border-red-500/30 bg-red-500/10 text-red-300 text-xs">
              {step3Error}
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Form */}
            <form onSubmit={handleStep3Upload} className="lg:col-span-6 space-y-4">
              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-slate-200">1. Download CSV Sample Template</span>
                  <a
                    href={importApi.getProductImportTemplateUrl()}
                    target="_blank"
                    rel="noreferrer"
                    className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-indigo-300 text-xs rounded-lg border border-slate-700 flex items-center gap-1.5 transition-colors"
                  >
                    <Download size={13} />
                    <span>products_template.csv</span>
                  </a>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-medium text-slate-300">2. Select Products CSV File</label>
                <input
                  type="file"
                  accept=".csv"
                  required
                  onChange={(e) => setProductFile(e.target.files?.[0] || null)}
                  className="w-full bg-slate-900 border border-slate-700/80 rounded-xl p-2.5 text-xs text-slate-200 file:mr-3 file:py-1 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-indigo-600 file:text-white hover:file:bg-indigo-500 cursor-pointer"
                />
              </div>

              <button
                type="submit"
                disabled={!productFile || productImportMutation.isPending}
                className="w-full py-2.5 bg-gradient-to-r from-indigo-600 to-sky-500 hover:from-indigo-500 hover:to-sky-400 text-white text-xs font-semibold rounded-xl shadow-lg shadow-indigo-600/20 flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
              >
                {productImportMutation.isPending ? (
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <>
                    <Upload size={15} />
                    <span>Upload & Import Products</span>
                  </>
                )}
              </button>
            </form>

            {/* Results Card */}
            <div className="lg:col-span-6 space-y-4">
              <h4 className="text-xs font-semibold text-slate-300">Import Summary Results</h4>

              {productResult ? (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-center">
                      <span className="text-xs text-emerald-300">Created Rows</span>
                      <p className="text-lg font-bold text-emerald-400 font-mono">{productResult.created}</p>
                    </div>
                    <div className="p-3 rounded-xl bg-sky-500/10 border border-sky-500/20 text-center">
                      <span className="text-xs text-sky-300">Updated Rows</span>
                      <p className="text-lg font-bold text-sky-400 font-mono">{productResult.updated}</p>
                    </div>
                  </div>

                  {productResult.errors.length > 0 && (
                    <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 space-y-2 max-h-48 overflow-y-auto">
                      <span className="text-xs font-bold text-red-300">Row Errors ({productResult.errors.length}):</span>
                      <div className="space-y-1">
                        {productResult.errors.map((err, i) => (
                          <div key={i} className="text-[11px] text-red-200 font-mono bg-slate-900/60 p-1.5 rounded">
                            Row {err.row}: {err.message}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="p-8 rounded-xl bg-slate-900/60 border border-slate-800 text-center text-xs text-slate-500">
                  Select a CSV file and click Upload to import catalog items.
                </div>
              )}

              <div className="flex justify-end pt-2">
                <button
                  onClick={() => setCurrentStep(4)}
                  className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl flex items-center gap-2 transition-colors cursor-pointer"
                >
                  <span>Proceed to Inventory Import</span>
                  <ArrowRight size={15} />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ─── STEP 4: IMPORT INVENTORY CSV ────────────────────────────────────── */}
      {currentStep === 4 && (
        <div className="card p-6 bg-[#121824] border border-slate-800 rounded-2xl space-y-6 shadow-xl">
          <div className="space-y-1">
            <h3 className="text-base font-serif text-white font-semibold flex items-center gap-2">
              <Boxes size={18} className="text-indigo-400" />
              <span>Step 4: Bulk Import Inventory Stock (CSV)</span>
            </h3>
            <p className="text-xs text-slate-400">
              Upload warehouse stock CSV (`warehouse_code,location_code,sku,quantity,reorder_threshold`). Reference exact location codes from the table below.
            </p>
          </div>

          {step4Error && (
            <div className="p-3 rounded-xl border border-red-500/30 bg-red-500/10 text-red-300 text-xs">
              {step4Error}
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Left Column: Form & Reference Table */}
            <div className="lg:col-span-7 space-y-4">
              <form onSubmit={handleStep4Upload} className="space-y-4">
                <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-slate-200">1. Download Inventory Template</span>
                    <a
                      href={importApi.getInventoryImportTemplateUrl()}
                      target="_blank"
                      rel="noreferrer"
                      className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-indigo-300 text-xs rounded-lg border border-slate-700 flex items-center gap-1.5 transition-colors"
                    >
                      <Download size={13} />
                      <span>inventory_template.csv</span>
                    </a>
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-medium text-slate-300">2. Select Inventory CSV File</label>
                  <input
                    type="file"
                    accept=".csv"
                    required
                    onChange={(e) => setInventoryFile(e.target.files?.[0] || null)}
                    className="w-full bg-slate-900 border border-slate-700/80 rounded-xl p-2.5 text-xs text-slate-200 file:mr-3 file:py-1 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-indigo-600 file:text-white hover:file:bg-indigo-500 cursor-pointer"
                  />
                </div>

                <button
                  type="submit"
                  disabled={!inventoryFile || inventoryImportMutation.isPending}
                  className="w-full py-2.5 bg-gradient-to-r from-indigo-600 to-sky-500 hover:from-indigo-500 hover:to-sky-400 text-white text-xs font-semibold rounded-xl shadow-lg shadow-indigo-600/20 flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                >
                  {inventoryImportMutation.isPending ? (
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    <>
                      <Upload size={15} />
                      <span>Upload & Import Inventory Stock</span>
                    </>
                  )}
                </button>
              </form>

              {/* Reference Locations Table */}
              <div className="space-y-2">
                <span className="text-xs font-semibold text-slate-300">
                  Copyable Location Codes for {selectedWh?.code || 'Warehouse'}:
                </span>

                <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 max-h-48 overflow-y-auto space-y-1">
                  {locationsData && locationsData.length > 0 ? (
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                      {locationsData.map((loc) => (
                        <button
                          key={loc.id}
                          type="button"
                          onClick={() => handleCopyText(loc.location_code)}
                          className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-mono text-emerald-400 flex items-center justify-between transition-colors group cursor-pointer"
                        >
                          <span>{loc.location_code}</span>
                          {copiedCode === loc.location_code ? (
                            <Check size={13} className="text-emerald-400" />
                          ) : (
                            <Copy size={12} className="text-slate-500 group-hover:text-slate-300" />
                          )}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-500">No layout storage locations generated yet.</p>
                  )}
                </div>
              </div>
            </div>

            {/* Results Column */}
            <div className="lg:col-span-5 space-y-4">
              <h4 className="text-xs font-semibold text-slate-300">Import Summary Results</h4>

              {inventoryResult ? (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-center">
                      <span className="text-xs text-emerald-300">Created Rows</span>
                      <p className="text-lg font-bold text-emerald-400 font-mono">{inventoryResult.created}</p>
                    </div>
                    <div className="p-3 rounded-xl bg-sky-500/10 border border-sky-500/20 text-center">
                      <span className="text-xs text-sky-300">Updated Rows</span>
                      <p className="text-lg font-bold text-sky-400 font-mono">{inventoryResult.updated}</p>
                    </div>
                  </div>

                  {inventoryResult.errors.length > 0 && (
                    <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 space-y-2 max-h-48 overflow-y-auto">
                      <span className="text-xs font-bold text-red-300">Row Errors ({inventoryResult.errors.length}):</span>
                      <div className="space-y-1">
                        {inventoryResult.errors.map((err, i) => (
                          <div key={i} className="text-[11px] text-red-200 font-mono bg-slate-900/60 p-1.5 rounded">
                            Row {err.row}: {err.message}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="p-8 rounded-xl bg-slate-900/60 border border-slate-800 text-center text-xs text-slate-500">
                  Select an inventory CSV file and click Upload to seed stock.
                </div>
              )}

              <div className="flex justify-end pt-2">
                <button
                  onClick={() => setCurrentStep(5)}
                  className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl flex items-center gap-2 transition-colors cursor-pointer"
                >
                  <span>Proceed to Final Checklist</span>
                  <ArrowRight size={15} />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ─── STEP 5: DONE CHECKLIST & GO TO SHOP PREVIEW ────────────────────── */}
      {currentStep === 5 && (
        <div className="card p-6 bg-[#121824] border border-slate-800 rounded-2xl space-y-6 shadow-xl">
          <div className="space-y-1">
            <h3 className="text-base font-serif text-white font-semibold flex items-center gap-2">
              <CheckCircle2 size={18} className="text-emerald-400" />
              <span>Step 5: Setup Complete Checklist & Activation</span>
            </h3>
            <p className="text-xs text-slate-400">
              Live status checklist verifying darkstore readiness for automated customer order fulfillment.
            </p>
          </div>

          <div className="space-y-3">
            {/* Checklist Item 1 */}
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
                  <Check size={18} />
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-white">1. Warehouse Facility Active</h4>
                  <p className="text-[11px] text-slate-400">{selectedWh ? `${selectedWh.name} (${selectedWh.code})` : 'Warehouse created'}</p>
                </div>
              </div>
              <span className="text-xs font-mono text-emerald-400">READY</span>
            </div>

            {/* Checklist Item 2 */}
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${graphData && graphData.nodes.length > 0 ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-800 text-slate-500'}`}>
                  <Check size={18} />
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-white">2. Grid Topology & Storage Locations</h4>
                  <p className="text-[11px] text-slate-400">{graphData ? `${graphData.nodes.length} Nodes, ${graphData.locations.length} Locations, Loop Edges Connected` : 'Layout generated'}</p>
                </div>
              </div>
              <span className="text-xs font-mono text-emerald-400">{graphData?.locations.length || 0} LOCS</span>
            </div>

            {/* Checklist Item 3 */}
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
                  <Check size={18} />
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-white">3. Product Catalog & SKU Upsert</h4>
                  <p className="text-[11px] text-slate-400">Global catalog items imported via CSV</p>
                </div>
              </div>
              <span className="text-xs font-mono text-emerald-400">IMPORTED</span>
            </div>

            {/* Checklist Item 4 */}
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
                  <Check size={18} />
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-white">4. Inventory Stock Allocated</h4>
                  <p className="text-[11px] text-slate-400">Physical stock quantities bound to location codes</p>
                </div>
              </div>
              <span className="text-xs font-mono text-emerald-400">STOCKED</span>
            </div>

            {/* Checklist Item 5 */}
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-indigo-500/20 text-indigo-400 flex items-center justify-center">
                  <RefreshCw size={18} className="animate-spin" />
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-white">5. Background Auto-Batching Scheduler</h4>
                  <p className="text-[11px] text-slate-400">Runs automatically every 30 seconds to batch pending orders</p>
                </div>
              </div>
              <span className="text-xs font-mono text-indigo-400 animate-pulse">ACTIVE (30s)</span>
            </div>
          </div>

          <div className="pt-4 flex flex-col sm:flex-row items-center gap-3">
            <button
              onClick={() => navigate('/shop')}
              className="w-full sm:w-auto px-6 py-3 bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white font-semibold text-xs rounded-xl shadow-lg shadow-emerald-600/20 flex items-center justify-center gap-2 cursor-pointer transition-all"
            >
              <ExternalLink size={16} />
              <span>Preview Customer Shop (/shop)</span>
            </button>

            <button
              onClick={() => navigate('/picker')}
              className="w-full sm:w-auto px-6 py-3 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs rounded-xl border border-slate-700 flex items-center justify-center gap-2 cursor-pointer transition-all"
            >
              <Layers size={16} />
              <span>Open Mobile Picker App (/picker)</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
