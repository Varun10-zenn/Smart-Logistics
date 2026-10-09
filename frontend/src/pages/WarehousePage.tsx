import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Warehouse,
  Layers,
  Package,
  Boxes,
  ShoppingCart,
  Zap,
  Plus,
  Trash2,
  Edit,
  CheckCircle2,
  AlertTriangle,
  X,
  Play,
  Navigation,
  ShieldAlert,
  Info,
  Grid
} from 'lucide-react';
import { AppShell } from '../components/layout/AppShell';
import { KpiCard } from '../components/ui/KpiCard';
import { SkeletonTable } from '../components/ui/Skeleton';
import { EmptyState } from '../components/ui/States';
import { StatusBadge } from '../components/ui/Badge';
import { useAuth } from '../contexts/AuthContext';
import { getRoleCode } from '../types/api';
import { warehouseApi } from '../api/warehouseApi';
import { WarehouseGraphCanvas } from '../components/WarehouseGraphCanvas';
import { OrderBatchList } from '../components/OrderBatchList';
import { PickRouteDetails } from '../components/PickRouteDetails';
import { AdminSetupWizard } from '../components/AdminSetupWizard';
import type {
  WarehouseRead,
  NodeRead,
  EdgeRead,
  ProductRead,
  BatchSummaryDTO,
  WarehouseOptimizationResultDTO,
} from '../types/api';

type TabType = 'setup' | 'warehouses' | 'layout' | 'products' | 'inventory' | 'orders' | 'optimize';

export function WarehousePage() {
  const { user } = useAuth();
  const role = getRoleCode(user?.role);
  const isAdmin = role === 'admin';
  const isOperator = role === 'warehouse_operator';
  const canWriteInventoryOrders = isAdmin || isOperator;

  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<TabType>('warehouses');

  // Active Warehouse state (persisted in localStorage)
  const [activeWarehouseId, setActiveWarehouseId] = useState<number | null>(() => {
    const saved = localStorage.getItem('activeWarehouseId');
    return saved ? parseInt(saved, 10) : null;
  });

  const handleSelectWarehouse = (id: number) => {
    setActiveWarehouseId(id);
    localStorage.setItem('activeWarehouseId', id.toString());
  };

  // Modals & Forms State
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  // 1. Warehouses Queries & Mutations
  const { data: warehousePage, isLoading: loadingWarehouses } = useQuery({
    queryKey: ['warehouses'],
    queryFn: () => warehouseApi.list({ page: 1, page_size: 100 }),
  });
  const warehouses = warehousePage?.items || [];

  useEffect(() => {
    if (warehouses.length > 0 && (activeWarehouseId === null || !warehouses.some((w) => w.id === activeWarehouseId))) {
      handleSelectWarehouse(warehouses[0].id);
    }
  }, [warehouses]);

  const [whModalOpen, setWhModalOpen] = useState(false);
  const [editingWh, setEditingWh] = useState<WarehouseRead | null>(null);
  const [whCode, setWhCode] = useState('');
  const [whName, setWhName] = useState('');
  const [whLat, setWhLat] = useState('12.9716');
  const [whLon, setWhLon] = useState('77.5946');
  const [whAddr, setWhAddr] = useState('');

  const createWhMutation = useMutation({
    mutationFn: warehouseApi.create,
    onSuccess: (newWh) => {
      queryClient.invalidateQueries({ queryKey: ['warehouses'] });
      handleSelectWarehouse(newWh.id);
      setWhModalOpen(false);
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail?.message || err.response?.data?.message || 'Failed to create warehouse.';
      setErrorBanner(msg);
    },
  });

  const updateWhMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => warehouseApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['warehouses'] });
      setWhModalOpen(false);
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail?.message || err.response?.data?.message || 'Failed to update warehouse.';
      setErrorBanner(msg);
    },
  });

  const deleteWhMutation = useMutation({
    mutationFn: warehouseApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['warehouses'] });
      setActiveWarehouseId(null);
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail?.message || err.response?.data?.message || 'Failed to delete warehouse.';
      setErrorBanner(msg);
    },
  });

  // 2. Layout Graph Queries & Mutations
  const { data: graphData } = useQuery({
    queryKey: ['warehouseGraph', activeWarehouseId],
    queryFn: () => (activeWarehouseId ? warehouseApi.getGraph(activeWarehouseId) : null),
    enabled: !!activeWarehouseId,
  });

  const nodes = graphData?.nodes || [];
  const edges = graphData?.edges || [];
  const locations = graphData?.locations || [];

  // Layout Canvas Interaction State
  const [selectedNode, setSelectedNode] = useState<NodeRead | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<EdgeRead | null>(null);
  const [connectMode, setConnectMode] = useState(false);
  const [connectSourceNodeId, setConnectSourceNodeId] = useState<number | null>(null);

  // Node Modal
  const [nodeModalOpen, setNodeModalOpen] = useState(false);
  const [nodeCode, setNodeCode] = useState('');
  const [nodeX, setNodeX] = useState(0);
  const [nodeY, setNodeY] = useState(0);
  const [nodeIsDepot, setNodeIsDepot] = useState(false);

  const createNodeMutation = useMutation({
    mutationFn: ({ whId, data }: { whId: number; data: any }) => warehouseApi.createNode(whId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['warehouseGraph', activeWarehouseId] });
      setNodeModalOpen(false);
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail?.message || err.response?.data?.message || 'Failed to create node.';
      setErrorBanner(msg);
    },
  });

  const updateNodeMutation = useMutation({
    mutationFn: ({ whId, nodeId, data }: { whId: number; nodeId: number; data: any }) =>
      warehouseApi.updateNode(whId, nodeId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['warehouseGraph', activeWarehouseId] });
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail?.message || err.response?.data?.message || 'Failed to update node.';
      setErrorBanner(msg);
    },
  });

  const deleteNodeMutation = useMutation({
    mutationFn: ({ whId, nodeId }: { whId: number; nodeId: number }) => warehouseApi.deleteNode(whId, nodeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['warehouseGraph', activeWarehouseId] });
      setSelectedNode(null);
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail?.message || err.response?.data?.message || 'Failed to delete node.';
      setErrorBanner(msg);
    },
  });

  // Edge Mutations
  const createEdgeMutation = useMutation({
    mutationFn: ({ whId, data }: { whId: number; data: any }) => warehouseApi.createEdge(whId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['warehouseGraph', activeWarehouseId] });
      setConnectMode(false);
      setConnectSourceNodeId(null);
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail?.message || err.response?.data?.message || 'Failed to create edge.';
      setErrorBanner(msg);
    },
  });

  useMutation({
    mutationFn: ({ whId, edgeId }: { whId: number; edgeId: number }) => warehouseApi.deleteEdge(whId, edgeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['warehouseGraph', activeWarehouseId] });
      setSelectedEdge(null);
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail?.message || err.response?.data?.message || 'Failed to delete edge.';
      setErrorBanner(msg);
    },
  });

  // Location Modal & Mutations
  const [locModalOpen, setLocModalOpen] = useState(false);
  const [locNodeId, setLocNodeId] = useState<number | null>(null);
  const [locCode, setLocCode] = useState('');
  const [locAisle, setLocAisle] = useState('A1');
  const [locShelf, setLocShelf] = useState('S1');
  const [locBin, setLocBin] = useState('B1');
  const [locMaxWeight] = useState('100.0');

  const createLocMutation = useMutation({
    mutationFn: ({ whId, data }: { whId: number; data: any }) => warehouseApi.createLocation(whId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['warehouseGraph', activeWarehouseId] });
      setLocModalOpen(false);
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail?.message || err.response?.data?.message || 'Failed to create location.';
      setErrorBanner(msg);
    },
  });

  const deleteLocMutation = useMutation({
    mutationFn: ({ whId, locId }: { whId: number; locId: number }) => warehouseApi.deleteLocation(whId, locId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['warehouseGraph', activeWarehouseId] });
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail?.message || err.response?.data?.message || 'Failed to delete location.';
      setErrorBanner(msg);
    },
  });

  // Layout Validation Query
  const { data: validationRes, refetch: refetchValidation } = useQuery({
    queryKey: ['warehouseValidation', activeWarehouseId],
    queryFn: () => (activeWarehouseId ? warehouseApi.validate(activeWarehouseId) : null),
    enabled: !!activeWarehouseId && activeTab === 'layout',
  });

  // 3. Products Queries & Mutations
  const { data: productPage } = useQuery({
    queryKey: ['products'],
    queryFn: () => warehouseApi.listProducts({ page: 1, page_size: 100 }),
  });
  const products = productPage?.items || [];

  const [prodModalOpen, setProdModalOpen] = useState(false);
  const [_editingProd, setEditingProd] = useState<ProductRead | null>(null);
  const [prodSku, setProdSku] = useState('');
  const [prodName, setProdName] = useState('');
  const [prodCategory] = useState('Electronics');
  const [prodWeight, setProdWeight] = useState('1.5');
  const [prodVolume, setProdVolume] = useState('0.01');
  const [prodPrice, setProdPrice] = useState('99.99');

  const createProdMutation = useMutation({
    mutationFn: warehouseApi.createProduct,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
      setProdModalOpen(false);
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail?.message || err.response?.data?.message || 'Failed to create product.';
      setErrorBanner(msg);
    },
  });

  const deleteProdMutation = useMutation({
    mutationFn: warehouseApi.deleteProduct,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail?.message || err.response?.data?.message || 'Failed to delete product.';
      setErrorBanner(msg);
    },
  });

  // 4. Inventory Queries & Mutations
  const { data: inventoryPage } = useQuery({
    queryKey: ['inventory', activeWarehouseId],
    queryFn: () => (activeWarehouseId ? warehouseApi.listInventory({ warehouse_id: activeWarehouseId, page_size: 100 }) : null),
    enabled: !!activeWarehouseId,
  });
  const inventoryItems = inventoryPage?.items || [];

  const [invModalOpen, setInvModalOpen] = useState(false);
  const [invLocId, setInvLocId] = useState<number | null>(null);
  const [invProdId, setInvProdId] = useState<number | null>(null);
  const [invQty, setInvQty] = useState('50');
  const [invThreshold, setInvThreshold] = useState('10');

  const upsertInvMutation = useMutation({
    mutationFn: warehouseApi.upsertInventory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventory', activeWarehouseId] });
      setInvModalOpen(false);
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail?.message || err.response?.data?.message || 'Failed to upsert inventory.';
      setErrorBanner(msg);
    },
  });

  const deleteInvMutation = useMutation({
    mutationFn: warehouseApi.deleteInventory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventory', activeWarehouseId] });
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail?.message || err.response?.data?.message || 'Failed to delete inventory.';
      setErrorBanner(msg);
    },
  });

  // 5. Orders Queries & Mutations
  const { data: orderPage } = useQuery({
    queryKey: ['orders', activeWarehouseId],
    queryFn: () => (activeWarehouseId ? warehouseApi.listOrders({ warehouse_id: activeWarehouseId, page_size: 100 }) : null),
    enabled: !!activeWarehouseId,
  });
  const orders = orderPage?.items || [];

  const [orderModalOpen, setOrderModalOpen] = useState(false);
  const [orderNum, setOrderNum] = useState('');
  const [custName, setCustName] = useState('Acme Corp');
  const [destAddr] = useState('100 Commercial St');
  const [destLat] = useState('12.9500');
  const [destLon] = useState('77.6000');
  const [orderPriority, setOrderPriority] = useState<'low' | 'normal' | 'high' | 'urgent'>('normal');
  const [promisedHours] = useState('6');
  const [orderItemRows, setOrderItemRows] = useState<{ product_id: number; quantity: number }[]>([]);

  const createOrderMutation = useMutation({
    mutationFn: warehouseApi.createOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders', activeWarehouseId] });
      setOrderModalOpen(false);
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail?.message || err.response?.data?.message || 'Failed to create order.';
      setErrorBanner(msg);
    },
  });

  const deleteOrderMutation = useMutation({
    mutationFn: warehouseApi.deleteOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders', activeWarehouseId] });
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail?.message || err.response?.data?.message || 'Failed to delete order.';
      setErrorBanner(msg);
    },
  });

  // 6. Optimization State & Mutation
  const [maxOrdersPerBatch] = useState('5');
  const [maxWeightKg] = useState('25.0');
  const [maxVolumeCbm] = useState('0.12');
  const [use2Opt] = useState(true);
  const [optResult, setOptResult] = useState<WarehouseOptimizationResultDTO | null>(null);
  const [selectedBatch, setSelectedBatch] = useState<BatchSummaryDTO | null>(null);

  const optimizeMutation = useMutation({
    mutationFn: ({ whId, payload }: { whId: number; payload: any }) => warehouseApi.optimize(whId, payload),
    onSuccess: (res) => {
      setOptResult(res);
      if (res.batches && res.batches.length > 0) {
        setSelectedBatch(res.batches[0]);
      }
      queryClient.invalidateQueries({ queryKey: ['orders', activeWarehouseId] });
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail?.message || err.response?.data?.message || 'Optimization failed.';
      setErrorBanner(msg);
    },
  });

  // Canvas Handlers
  const handleCanvasClick = (x: number, y: number) => {
    if (!isAdmin) return;
    if (connectMode && connectSourceNodeId !== null) {
      setConnectMode(false);
      setConnectSourceNodeId(null);
      return;
    }
    setNodeCode(`N-${nodes.length + 1}`);
    setNodeX(x);
    setNodeY(y);
    setNodeIsDepot(nodes.length === 0);
    setNodeModalOpen(true);
  };

  const handleNodeClick = (node: NodeRead) => {
    if (connectMode) {
      if (connectSourceNodeId === null) {
        setConnectSourceNodeId(node.id);
      } else if (connectSourceNodeId !== node.id) {
        createEdgeMutation.mutate({
          whId: activeWarehouseId!,
          data: { from_node_id: connectSourceNodeId, to_node_id: node.id, is_bidirectional: true },
        });
      }
    } else {
      setSelectedNode(node);
      setSelectedEdge(null);
    }
  };

  const handleNodeDragEnd = (nodeId: number, newX: number, newY: number) => {
    if (!isAdmin || !activeWarehouseId) return;
    updateNodeMutation.mutate({
      whId: activeWarehouseId,
      nodeId,
      data: { x_coord: newX, y_coord: newY },
    });
  };

  const activeWarehouse = warehouses.find((w) => w.id === activeWarehouseId);

  return (
    <AppShell title="Warehouse">
      <div className="space-y-6 max-w-7xl mx-auto pb-12">
        {/* Header & Warehouse Selector */}
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div>
            <h2 className="font-serif text-2xl text-slate-100 flex items-center gap-2.5">
              <Warehouse size={24} className="text-indigo-400" />
              <span>Warehouse Operations & Layout Studio</span>
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              User-driven warehouse configuration, indoor dark-store graph editor, stock management, and picking route optimization.
            </p>
          </div>

          {/* Active Warehouse Picker (Searchable / Filterable) */}
          {warehouses.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 bg-slate-900/80 p-1.5 rounded-xl border border-slate-800">
              <span className="text-xs font-medium text-slate-400 pl-2">Active:</span>
              <select
                value={activeWarehouseId || ''}
                onChange={(e) => handleSelectWarehouse(parseInt(e.target.value, 10))}
                className="bg-slate-800 border border-slate-700 text-slate-100 text-xs font-semibold rounded-lg px-3 py-1.5 focus:outline-none focus:border-indigo-500 max-w-xs truncate"
              >
                {warehouses.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.code} - {w.name}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* Global Error Banner Callout */}
        {errorBanner && (
          <div className="p-4 rounded-xl border border-red-500/40 bg-red-950/40 text-red-300 text-xs flex items-start justify-between gap-3 shadow-lg animate-fade-in">
            <div className="flex items-start gap-2">
              <ShieldAlert size={18} className="text-red-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold block text-red-200">Server Error Response</span>
                <span>{errorBanner}</span>
              </div>
            </div>
            <button onClick={() => setErrorBanner(null)} className="text-red-400 hover:text-white">
              <X size={16} />
            </button>
          </div>
        )}

        {/* Navigation Tabs */}
        <div className="flex items-center gap-1 border-b border-slate-800/90 overflow-x-auto">
          {[
            { id: 'setup', label: 'Setup Wizard', icon: <Grid size={16} />, adminOnly: true },
            { id: 'warehouses', label: 'Warehouses', icon: <Warehouse size={16} />, badge: warehouses.length },
            { id: 'layout', label: 'Layout Editor', icon: <Layers size={16} />, badge: nodes.length, adminOnly: true },
            { id: 'products', label: 'Products', icon: <Package size={16} />, badge: products.length, adminOnly: true },
            { id: 'inventory', label: 'Inventory', icon: <Boxes size={16} />, badge: inventoryItems.length },
            { id: 'orders', label: 'Orders', icon: <ShoppingCart size={16} />, badge: orders.length },
            { id: 'optimize', label: 'Optimize', icon: <Zap size={16} /> },
          ].map((tab) => {
            if (tab.adminOnly && !isAdmin) return null;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as TabType)}
                className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-all cursor-pointer whitespace-nowrap ${
                  isActive
                    ? 'border-indigo-500 text-indigo-400 bg-indigo-500/10'
                    : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
                }`}
              >
                {tab.icon}
                <span>{tab.label}</span>
                {tab.badge !== undefined && (
                  <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${isActive ? 'bg-indigo-500/20 text-indigo-300' : 'bg-slate-800 text-slate-400'}`}>
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* --- TAB 0: SETUP WIZARD --- */}
        {activeTab === 'setup' && (
          <AdminSetupWizard
            activeWarehouseId={activeWarehouseId}
            onSelectWarehouse={handleSelectWarehouse}
            warehouses={warehouses}
          />
        )}

        {/* --- TAB 1: WAREHOUSES MASTER --- */}
        {activeTab === 'warehouses' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-200">Warehouses Master Directory</h3>
              {isAdmin && (
                <button
                  onClick={() => {
                    setEditingWh(null);
                    setWhCode(`WH-${Math.floor(100 + Math.random() * 900)}`);
                    setWhName('');
                    setWhAddr('');
                    setWhModalOpen(true);
                  }}
                  className="py-2 px-3 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 cursor-pointer shadow-md"
                >
                  <Plus size={15} />
                  <span>Create Warehouse</span>
                </button>
              )}
            </div>

            {loadingWarehouses ? (
              <SkeletonTable rows={4} />
            ) : warehouses.length === 0 ? (
              <EmptyState title="No warehouses found." description="Create your first warehouse to get started." />
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {warehouses.map((w) => {
                  const isSelected = activeWarehouseId === w.id;
                  return (
                    <div
                      key={w.id}
                      className={`p-4 rounded-xl border transition-all ${
                        isSelected
                          ? 'border-indigo-500 bg-indigo-950/30 shadow-lg shadow-indigo-950/40'
                          : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-mono text-xs font-bold text-indigo-400">{w.code}</span>
                        <StatusBadge status={w.status} />
                      </div>
                      <h4 className="font-semibold text-sm text-slate-100 mb-1">{w.name}</h4>
                      <p className="text-xs text-slate-400 line-clamp-1 mb-3">{w.address || 'No address provided.'}</p>
                      <div className="flex items-center justify-between pt-2 border-t border-slate-800/80 text-xs">
                        <button
                          onClick={() => handleSelectWarehouse(w.id)}
                          className={`px-3 py-1 rounded-md text-xs font-medium cursor-pointer ${
                            isSelected ? 'bg-indigo-500 text-white' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                          }`}
                        >
                          {isSelected ? 'Active' : 'Select'}
                        </button>
                        {isAdmin && (
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => {
                                setEditingWh(w);
                                setWhCode(w.code);
                                setWhName(w.name);
                                setWhLat(w.latitude.toString());
                                setWhLon(w.longitude.toString());
                                setWhAddr(w.address || '');
                                setWhModalOpen(true);
                              }}
                              className="p-1.5 text-slate-400 hover:text-sky-400"
                            >
                              <Edit size={14} />
                            </button>
                            <button
                              onClick={() => {
                                if (confirm(`Delete warehouse ${w.name}?`)) {
                                  deleteWhMutation.mutate(w.id);
                                }
                              }}
                              className="p-1.5 text-slate-400 hover:text-red-400"
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* --- TAB 2: LAYOUT EDITOR (ADMIN) --- */}
        {activeTab === 'layout' && (
          <div className="space-y-4">
            {!activeWarehouseId ? (
              <EmptyState title="No active warehouse selected." description="Select or create a warehouse first." />
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
                {/* Main Graph Canvas */}
                <div className="lg:col-span-8 space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-slate-200">
                      Indoor Layout Editor — {activeWarehouse?.name}
                    </h3>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setConnectMode(!connectMode)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 cursor-pointer border ${
                          connectMode
                            ? 'bg-sky-500/20 border-sky-400 text-sky-300 animate-pulse'
                            : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'
                        }`}
                      >
                        <Navigation size={14} />
                        <span>{connectMode ? 'Cancel Connect Mode' : 'Connect Nodes Mode'}</span>
                      </button>
                      <button
                        onClick={() => refetchValidation()}
                        className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold cursor-pointer shadow-md"
                      >
                        Validate Layout
                      </button>
                    </div>
                  </div>

                  <WarehouseGraphCanvas
                    nodes={nodes}
                    edges={edges}
                    locations={locations}
                    selectedNodeId={selectedNode?.id}
                    selectedEdgeId={selectedEdge?.id}
                    connectMode={connectMode}
                    connectSourceNodeId={connectSourceNodeId}
                    onCanvasClick={handleCanvasClick}
                    onNodeClick={handleNodeClick}
                    onNodeDragEnd={handleNodeDragEnd}
                    onEdgeClick={(e) => {
                      setSelectedEdge(e);
                      setSelectedNode(null);
                    }}
                  />

                  {/* Validation Results Callout */}
                  {validationRes && (
                    <div className={`p-4 rounded-xl border ${validationRes.valid ? 'border-emerald-500/30 bg-emerald-950/20 text-emerald-300' : 'border-red-500/40 bg-red-950/30 text-red-300'}`}>
                      <div className="flex items-center gap-2 font-bold text-xs mb-1">
                        {validationRes.valid ? <CheckCircle2 size={16} className="text-emerald-400" /> : <AlertTriangle size={16} className="text-red-400" />}
                        <span>{validationRes.valid ? 'Layout Graph Valid & Ready for Optimization' : 'Layout Validation Errors Found'}</span>
                      </div>
                      {!validationRes.valid && (
                        <ul className="list-disc list-inside text-xs space-y-1 pl-2">
                          {validationRes.errors.map((err, idx) => (
                            <li key={idx}>{err}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                </div>

                {/* Right Side Inspector & Entity Lists Panel */}
                <div className="lg:col-span-4 space-y-4">
                  {/* Selected Node Panel */}
                  {selectedNode && (
                    <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/80 space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-xs text-slate-200">Selected Node: {selectedNode.node_code}</span>
                        <button onClick={() => setSelectedNode(null)} className="text-slate-400 hover:text-white">
                          <X size={14} />
                        </button>
                      </div>

                      <div className="text-xs text-slate-400 space-y-1">
                        <p>Coords: ({selectedNode.x_coord}, {selectedNode.y_coord})</p>
                        <p>Role: {selectedNode.is_depot ? <span className="text-emerald-400 font-bold">DEPOT NODE</span> : 'Standard Node'}</p>
                      </div>

                      <div className="flex flex-wrap gap-2 pt-2 border-t border-slate-800">
                        {!selectedNode.is_depot && (
                          <button
                            onClick={() =>
                              updateNodeMutation.mutate({
                                whId: activeWarehouseId!,
                                nodeId: selectedNode.id,
                                data: { is_depot: true },
                              })
                            }
                            className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded cursor-pointer"
                          >
                            Set as Depot
                          </button>
                        )}

                        <button
                          onClick={() =>
                            updateNodeMutation.mutate({
                              whId: activeWarehouseId!,
                              nodeId: selectedNode.id,
                              data: { is_blocked: !selectedNode.is_blocked },
                            })
                          }
                          className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded cursor-pointer"
                        >
                          {selectedNode.is_blocked ? 'Unblock Node' : 'Block Node'}
                        </button>

                        <button
                          onClick={() => {
                            setLocNodeId(selectedNode.id);
                            setLocCode(`LOC-${selectedNode.node_code}-01`);
                            setLocModalOpen(true);
                          }}
                          className="px-2.5 py-1 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded cursor-pointer"
                        >
                          Add Location
                        </button>

                        <button
                          onClick={() => deleteNodeMutation.mutate({ whId: activeWarehouseId!, nodeId: selectedNode.id })}
                          className="px-2.5 py-1 bg-red-600/80 hover:bg-red-500 text-white text-xs font-medium rounded cursor-pointer"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Side Entity Lists */}
                  <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 space-y-3 max-h-[350px] overflow-y-auto">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">Layout Storage Locations ({locations.length})</h4>
                    {locations.length === 0 ? (
                      <p className="text-xs text-slate-500">No storage locations created yet.</p>
                    ) : (
                      <div className="space-y-1.5">
                        {locations.map((loc) => (
                          <div key={loc.id} className="flex items-center justify-between p-2 rounded bg-slate-800/60 text-xs">
                            <div>
                              <span className="font-mono font-semibold text-slate-100">{loc.location_code}</span>
                              <span className="text-slate-400 block text-[10px]">{loc.aisle}-{loc.shelf}-{loc.bin}</span>
                            </div>
                            <button
                              onClick={() => deleteLocMutation.mutate({ whId: activeWarehouseId!, locId: loc.id })}
                              className="text-slate-400 hover:text-red-400 p-1"
                            >
                              <Trash2 size={13} />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* --- TAB 3: PRODUCTS (ADMIN) --- */}
        {activeTab === 'products' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-200">Global Product Catalog ({products.length})</h3>
              {isAdmin && (
                <button
                  onClick={() => {
                    setEditingProd(null);
                    setProdSku(`SKU-${Math.floor(1000 + Math.random() * 9000)}`);
                    setProdName('');
                    setProdModalOpen(true);
                  }}
                  className="py-2 px-3 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 cursor-pointer shadow-md"
                >
                  <Plus size={15} />
                  <span>Create Product</span>
                </button>
              )}
            </div>

            <div className="card overflow-hidden">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-slate-800 bg-slate-900/80 text-slate-400 font-medium">
                    <th className="text-left px-4 py-3">SKU</th>
                    <th className="text-left px-4 py-3">Product Name</th>
                    <th className="text-left px-4 py-3">Category</th>
                    <th className="text-right px-4 py-3">Unit Weight (kg)</th>
                    <th className="text-right px-4 py-3">Unit Volume (cbm)</th>
                    <th className="text-right px-4 py-3">Price ($)</th>
                    {isAdmin && <th className="text-right px-4 py-3">Actions</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-200">
                  {products.map((p) => (
                    <tr key={p.id} className="hover:bg-slate-900/40">
                      <td className="px-4 py-2.5 font-mono text-indigo-400 font-semibold">{p.sku}</td>
                      <td className="px-4 py-2.5 font-medium text-slate-100">{p.name}</td>
                      <td className="px-4 py-2.5 text-slate-400">{p.category}</td>
                      <td className="px-4 py-2.5 text-right font-mono">{p.unit_weight_kg}</td>
                      <td className="px-4 py-2.5 text-right font-mono">{p.unit_volume_cbm}</td>
                      <td className="px-4 py-2.5 text-right font-mono">${p.price.toFixed(2)}</td>
                      {isAdmin && (
                        <td className="px-4 py-2.5 text-right">
                          <button
                            onClick={() => {
                              if (confirm(`Delete product ${p.sku}?`)) {
                                deleteProdMutation.mutate(p.id);
                              }
                            }}
                            className="text-slate-400 hover:text-red-400 p-1"
                          >
                            <Trash2 size={14} />
                          </button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* --- TAB 4: INVENTORY --- */}
        {activeTab === 'inventory' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-200">
                Warehouse Stock Inventory — {activeWarehouse?.name} ({inventoryItems.length})
              </h3>
              {canWriteInventoryOrders && (
                <button
                  onClick={() => {
                    setInvLocId(locations[0]?.id || null);
                    setInvProdId(products[0]?.id || null);
                    setInvModalOpen(true);
                  }}
                  className="py-2 px-3 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 cursor-pointer shadow-md"
                >
                  <Plus size={15} />
                  <span>Upsert Stock</span>
                </button>
              )}
            </div>

            <div className="card overflow-hidden">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-slate-800 bg-slate-900/80 text-slate-400 font-medium">
                    <th className="text-left px-4 py-3">Product SKU</th>
                    <th className="text-left px-4 py-3">Location Code</th>
                    <th className="text-right px-4 py-3">Available Quantity</th>
                    <th className="text-right px-4 py-3">Reorder Threshold</th>
                    {canWriteInventoryOrders && <th className="text-right px-4 py-3">Actions</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-200">
                  {inventoryItems.map((inv) => {
                    const prod = products.find((p) => p.id === inv.product_id);
                    const loc = locations.find((l) => l.id === inv.location_id);
                    return (
                      <tr key={inv.id} className="hover:bg-slate-900/40">
                        <td className="px-4 py-2.5 font-mono text-indigo-400 font-semibold">{prod?.sku || inv.product_id}</td>
                        <td className="px-4 py-2.5 font-mono text-slate-300">{loc?.location_code || inv.location_id}</td>
                        <td className="px-4 py-2.5 text-right font-mono font-bold text-emerald-400">{inv.quantity}</td>
                        <td className="px-4 py-2.5 text-right font-mono text-slate-400">{inv.reorder_threshold}</td>
                        {canWriteInventoryOrders && (
                          <td className="px-4 py-2.5 text-right">
                            <button
                              onClick={() => deleteInvMutation.mutate(inv.id)}
                              className="text-slate-400 hover:text-red-400 p-1"
                            >
                              <Trash2 size={14} />
                            </button>
                          </td>
                        )}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* --- TAB 5: ORDERS --- */}
        {activeTab === 'orders' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-200">
                Outbound Orders — {activeWarehouse?.name} ({orders.length})
              </h3>
              {canWriteInventoryOrders && (
                <button
                  onClick={() => {
                    setOrderNum(`ORD-${Math.floor(10000 + Math.random() * 90000)}`);
                    setOrderItemRows([{ product_id: products[0]?.id || 1, quantity: 2 }]);
                    setOrderModalOpen(true);
                  }}
                  className="py-2 px-3 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 cursor-pointer shadow-md"
                >
                  <Plus size={15} />
                  <span>Create Order</span>
                </button>
              )}
            </div>

            <div className="card overflow-hidden">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-slate-800 bg-slate-900/80 text-slate-400 font-medium">
                    <th className="text-left px-4 py-3">Order Number</th>
                    <th className="text-left px-4 py-3">Customer</th>
                    <th className="text-left px-4 py-3">Priority</th>
                    <th className="text-left px-4 py-3">Status</th>
                    <th className="text-right px-4 py-3">Items Count</th>
                    {canWriteInventoryOrders && <th className="text-right px-4 py-3">Actions</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-200">
                  {orders.map((o) => (
                    <tr key={o.id} className="hover:bg-slate-900/40">
                      <td className="px-4 py-2.5 font-mono text-indigo-400 font-semibold">{o.order_number}</td>
                      <td className="px-4 py-2.5 font-medium text-slate-100">{o.customer_name || 'N/A'}</td>
                      <td className="px-4 py-2.5 capitalize">{o.priority}</td>
                      <td className="px-4 py-2.5"><StatusBadge status={o.status} /></td>
                      <td className="px-4 py-2.5 text-right font-mono">{o.items.length}</td>
                      {canWriteInventoryOrders && (
                        <td className="px-4 py-2.5 text-right">
                          {o.status === 'pending' && (
                            <button
                              onClick={() => deleteOrderMutation.mutate(o.id)}
                              className="text-slate-400 hover:text-red-400 p-1"
                            >
                              <Trash2 size={14} />
                            </button>
                          )}
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* --- TAB 6: OPTIMIZE --- */}
        {activeTab === 'optimize' && (
          <div className="space-y-6">
            <div className="p-3 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs flex items-center gap-2">
              <Info size={16} className="shrink-0" />
              <span>Note: Order batching and pick route optimization also runs automatically in the background every 30 seconds for active warehouses with pending orders.</span>
            </div>

            <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/80 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
              <div>
                <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
                  <Zap size={18} className="text-amber-400" />
                  <span>Batching & Pick Route Optimization Engine</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Runs Priority-Heuristic batch grouping and Nearest-Neighbor + 2-Opt local search route optimization over the dark-store layout.
                </p>
              </div>

              <button
                onClick={() => {
                  optimizeMutation.mutate({
                    whId: activeWarehouseId!,
                    payload: {
                      constraints: {
                        max_orders_per_batch: parseInt(maxOrdersPerBatch, 10),
                        max_weight_kg: parseFloat(maxWeightKg),
                        max_volume_cbm: parseFloat(maxVolumeCbm),
                      },
                      use_2opt_routing: use2Opt,
                    },
                  });
                }}
                disabled={optimizeMutation.isPending || !activeWarehouseId}
                className="py-2.5 px-5 bg-gradient-to-r from-amber-500 to-indigo-600 hover:from-amber-400 hover:to-indigo-500 text-white font-semibold text-xs rounded-xl shadow-lg shadow-amber-500/20 flex items-center gap-2 disabled:opacity-50 cursor-pointer"
              >
                {optimizeMutation.isPending ? (
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <>
                    <Play size={15} />
                    <span>Run Optimization</span>
                  </>
                )}
              </button>
            </div>

            {/* Optimization Results Panel */}
            {optResult && (
              <div className="space-y-6">
                {/* Result KPI Metrics Header */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                  <KpiCard label="Batches Created" value={optResult.generated_batches_count} lead />
                  <KpiCard label="Eligible Orders" value={optResult.eligible_orders_count} />
                  <KpiCard
                    label="Distance Reduction"
                    value={optResult.overall_distance_reduction_pct ? `${optResult.overall_distance_reduction_pct}%` : '0%'}
                  />
                  <KpiCard label="Execution Time" value={`${optResult.execution_time_ms}ms`} />
                </div>

                {/* Graph Visualization with Selected Batch Pick Path */}
                {selectedBatch && (
                  <div className="space-y-2">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                      Visualized Route Path: {selectedBatch.batch_code}
                    </h4>
                    <WarehouseGraphCanvas
                      nodes={nodes}
                      edges={edges}
                      locations={locations}
                      readOnly
                    />
                  </div>
                )}

                {/* Order Batches List & Unassigned Callouts */}
                <OrderBatchList
                  batches={optResult.batches}
                  unassignedOrderIds={optResult.unassigned_order_ids}
                  unassignedReasons={optResult.unassigned_reasons}
                  selectedBatchId={selectedBatch?.batch_id}
                  onSelectBatch={(b) => setSelectedBatch(b)}
                />

                {selectedBatch && <PickRouteDetails batch={selectedBatch} />}
              </div>
            )}
          </div>
        )}
      </div>

      {/* --- MODAL: CREATE / EDIT WAREHOUSE --- */}
      {whModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-[#121824] border border-slate-800 rounded-2xl p-6 space-y-4 shadow-2xl">
            <h3 className="text-lg font-serif text-slate-100">{editingWh ? 'Edit Warehouse' : 'Create Warehouse'}</h3>
            <div className="space-y-3 text-xs">
              <div>
                <label className="text-slate-300 font-medium">Warehouse Code</label>
                <input
                  type="text"
                  value={whCode}
                  onChange={(e) => setWhCode(e.target.value)}
                  disabled={!!editingWh}
                  className="w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100 font-mono"
                />
              </div>
              <div>
                <label className="text-slate-300 font-medium">Warehouse Name</label>
                <input
                  type="text"
                  value={whName}
                  onChange={(e) => setWhName(e.target.value)}
                  placeholder="Central Hub"
                  className="w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-slate-300 font-medium">Latitude</label>
                  <input
                    type="text"
                    value={whLat}
                    onChange={(e) => setWhLat(e.target.value)}
                    className="w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100 font-mono"
                  />
                </div>
                <div>
                  <label className="text-slate-300 font-medium">Longitude</label>
                  <input
                    type="text"
                    value={whLon}
                    onChange={(e) => setWhLon(e.target.value)}
                    className="w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100 font-mono"
                  />
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button onClick={() => setWhModalOpen(false)} className="px-3 py-1.5 bg-slate-800 text-slate-300 rounded-lg text-xs">
                Cancel
              </button>
              <button
                onClick={() => {
                  if (editingWh) {
                    updateWhMutation.mutate({ id: editingWh.id, data: { name: whName, address: whAddr } });
                  } else {
                    createWhMutation.mutate({ code: whCode, name: whName, latitude: parseFloat(whLat), longitude: parseFloat(whLon), address: whAddr });
                  }
                }}
                className="px-4 py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-semibold"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {/* --- MODAL: ADD NODE --- */}
      {nodeModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-sm bg-[#121824] border border-slate-800 rounded-2xl p-6 space-y-4 shadow-2xl">
            <h3 className="text-sm font-semibold text-slate-100">Add Layout Node</h3>
            <div className="space-y-3 text-xs">
              <div>
                <label className="text-slate-300 font-medium">Node Code</label>
                <input
                  type="text"
                  value={nodeCode}
                  onChange={(e) => setNodeCode(e.target.value)}
                  className="w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100 font-mono"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-slate-300 font-medium">X Coord</label>
                  <input
                    type="number"
                    value={nodeX}
                    onChange={(e) => setNodeX(parseFloat(e.target.value))}
                    className="w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100 font-mono"
                  />
                </div>
                <div>
                  <label className="text-slate-300 font-medium">Y Coord</label>
                  <input
                    type="number"
                    value={nodeY}
                    onChange={(e) => setNodeY(parseFloat(e.target.value))}
                    className="w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100 font-mono"
                  />
                </div>
              </div>
              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="chkDepot"
                  checked={nodeIsDepot}
                  onChange={(e) => setNodeIsDepot(e.target.checked)}
                  className="rounded border-slate-700 text-emerald-500 focus:ring-emerald-500"
                />
                <label htmlFor="chkDepot" className="text-slate-200 font-medium">
                  Set as Warehouse Depot Start/End Point
                </label>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button onClick={() => setNodeModalOpen(false)} className="px-3 py-1.5 bg-slate-800 text-slate-300 rounded-lg text-xs">
                Cancel
              </button>
              <button
                onClick={() =>
                  createNodeMutation.mutate({
                    whId: activeWarehouseId!,
                    data: { node_code: nodeCode, x_coord: nodeX, y_coord: nodeY, is_depot: nodeIsDepot },
                  })
                }
                className="px-4 py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-semibold"
              >
                Add Node
              </button>
            </div>
          </div>
        </div>
      )}

      {/* --- MODAL: ADD LOCATION --- */}
      {locModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-sm bg-[#121824] border border-slate-800 rounded-2xl p-6 space-y-4 shadow-2xl">
            <h3 className="text-sm font-semibold text-slate-100">Add Storage Location</h3>
            <div className="space-y-3 text-xs">
              <div>
                <label className="text-slate-300 font-medium">Location Code</label>
                <input
                  type="text"
                  value={locCode}
                  onChange={(e) => setLocCode(e.target.value)}
                  className="w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100 font-mono"
                />
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className="text-slate-300 font-medium">Aisle</label>
                  <input
                    type="text"
                    value={locAisle}
                    onChange={(e) => setLocAisle(e.target.value)}
                    className="w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100"
                  />
                </div>
                <div>
                  <label className="text-slate-300 font-medium">Shelf</label>
                  <input
                    type="text"
                    value={locShelf}
                    onChange={(e) => setLocShelf(e.target.value)}
                    className="w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100"
                  />
                </div>
                <div>
                  <label className="text-slate-300 font-medium">Bin</label>
                  <input
                    type="text"
                    value={locBin}
                    onChange={(e) => setLocBin(e.target.value)}
                    className="w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100"
                  />
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button onClick={() => setLocModalOpen(false)} className="px-3 py-1.5 bg-slate-800 text-slate-300 rounded-lg text-xs">
                Cancel
              </button>
              <button
                onClick={() =>
                  createLocMutation.mutate({
                    whId: activeWarehouseId!,
                    data: {
                      node_id: locNodeId!,
                      location_code: locCode,
                      aisle: locAisle,
                      shelf: locShelf,
                      bin: locBin,
                      max_weight_kg: parseFloat(locMaxWeight),
                    },
                  })
                }
                className="px-4 py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-semibold"
              >
                Add Location
              </button>
            </div>
          </div>
        </div>
      )}

      {/* --- MODAL: CREATE PRODUCT --- */}
      {prodModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-[#121824] border border-slate-800 rounded-2xl p-6 space-y-4 shadow-2xl">
            <h3 className="text-sm font-semibold text-slate-100">Create Global Product SKU</h3>
            <div className="space-y-3 text-xs">
              <div>
                <label className="text-slate-300 font-medium">Product SKU</label>
                <input
                  type="text"
                  value={prodSku}
                  onChange={(e) => setProdSku(e.target.value)}
                  className="w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100 font-mono"
                />
              </div>
              <div>
                <label className="text-slate-300 font-medium">Product Name</label>
                <input
                  type="text"
                  value={prodName}
                  onChange={(e) => setProdName(e.target.value)}
                  placeholder="Smart Tracker"
                  className="w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100"
                />
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className="text-slate-300 font-medium">Weight (kg)</label>
                  <input
                    type="number"
                    value={prodWeight}
                    onChange={(e) => setProdWeight(e.target.value)}
                    className="w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100 font-mono"
                  />
                </div>
                <div>
                  <label className="text-slate-300 font-medium">Volume (cbm)</label>
                  <input
                    type="number"
                    value={prodVolume}
                    onChange={(e) => setProdVolume(e.target.value)}
                    className="w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100 font-mono"
                  />
                </div>
                <div>
                  <label className="text-slate-300 font-medium">Price ($)</label>
                  <input
                    type="number"
                    value={prodPrice}
                    onChange={(e) => setProdPrice(e.target.value)}
                    className="w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100 font-mono"
                  />
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button onClick={() => setProdModalOpen(false)} className="px-3 py-1.5 bg-slate-800 text-slate-300 rounded-lg text-xs">
                Cancel
              </button>
              <button
                onClick={() =>
                  createProdMutation.mutate({
                    sku: prodSku,
                    name: prodName,
                    category: prodCategory,
                    unit_weight_kg: parseFloat(prodWeight),
                    unit_volume_cbm: parseFloat(prodVolume),
                    price: parseFloat(prodPrice),
                  })
                }
                className="px-4 py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-semibold"
              >
                Create Product
              </button>
            </div>
          </div>
        </div>
      )}

      {/* --- MODAL: UPSERT INVENTORY --- */}
      {invModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-sm bg-[#121824] border border-slate-800 rounded-2xl p-6 space-y-4 shadow-2xl">
            <h3 className="text-sm font-semibold text-slate-100">Upsert Inventory Stock</h3>
            <div className="space-y-3 text-xs">
              <div>
                <label className="text-slate-300 font-medium">Select Storage Location</label>
                <select
                  value={invLocId || ''}
                  onChange={(e) => setInvLocId(parseInt(e.target.value, 10))}
                  className="w-full mt-1 bg-slate-900 border border-slate-700 text-slate-100 rounded-lg p-2"
                >
                  {locations.map((loc) => (
                    <option key={loc.id} value={loc.id}>
                      {loc.location_code} ({loc.aisle}-{loc.shelf}-{loc.bin})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-slate-300 font-medium">Select Product SKU</label>
                <select
                  value={invProdId || ''}
                  onChange={(e) => setInvProdId(parseInt(e.target.value, 10))}
                  className="w-full mt-1 bg-slate-900 border border-slate-700 text-slate-100 rounded-lg p-2"
                >
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.sku} - {p.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-slate-300 font-medium">Quantity</label>
                  <input
                    type="number"
                    value={invQty}
                    onChange={(e) => setInvQty(e.target.value)}
                    className="w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100 font-mono"
                  />
                </div>
                <div>
                  <label className="text-slate-300 font-medium">Threshold</label>
                  <input
                    type="number"
                    value={invThreshold}
                    onChange={(e) => setInvThreshold(e.target.value)}
                    className="w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100 font-mono"
                  />
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button onClick={() => setInvModalOpen(false)} className="px-3 py-1.5 bg-slate-800 text-slate-300 rounded-lg text-xs">
                Cancel
              </button>
              <button
                onClick={() =>
                  upsertInvMutation.mutate({
                    warehouse_id: activeWarehouseId!,
                    location_id: invLocId!,
                    product_id: invProdId!,
                    quantity: parseInt(invQty, 10),
                    reorder_threshold: parseInt(invThreshold, 10),
                  })
                }
                className="px-4 py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-semibold"
              >
                Save Stock
              </button>
            </div>
          </div>
        </div>
      )}

      {/* --- MODAL: CREATE ORDER --- */}
      {orderModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-[#121824] border border-slate-800 rounded-2xl p-6 space-y-4 shadow-2xl">
            <h3 className="text-sm font-semibold text-slate-100">Create Outbound Order</h3>
            <div className="space-y-3 text-xs">
              <div>
                <label className="text-slate-300 font-medium">Order Number</label>
                <input
                  type="text"
                  value={orderNum}
                  onChange={(e) => setOrderNum(e.target.value)}
                  className="w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100 font-mono"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-slate-300 font-medium">Customer Name</label>
                  <input
                    type="text"
                    value={custName}
                    onChange={(e) => setCustName(e.target.value)}
                    className="w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100"
                  />
                </div>
                <div>
                  <label className="text-slate-300 font-medium">Priority</label>
                  <select
                    value={orderPriority}
                    onChange={(e) => setOrderPriority(e.target.value as any)}
                    className="w-full mt-1 bg-slate-900 border border-slate-700 text-slate-100 rounded-lg p-2"
                  >
                    <option value="normal">Normal</option>
                    <option value="high">High</option>
                    <option value="urgent">Urgent</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-slate-300 font-medium">Order Line Items</label>
                {orderItemRows.map((row, idx) => (
                  <div key={idx} className="flex items-center gap-2 mt-1.5">
                    <select
                      value={row.product_id}
                      onChange={(e) => {
                        const next = [...orderItemRows];
                        next[idx].product_id = parseInt(e.target.value, 10);
                        setOrderItemRows(next);
                      }}
                      className="flex-1 bg-slate-900 border border-slate-700 text-slate-100 rounded-lg p-1.5 text-xs"
                    >
                      {products.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.sku} - {p.name}
                        </option>
                      ))}
                    </select>
                    <input
                      type="number"
                      value={row.quantity}
                      onChange={(e) => {
                        const next = [...orderItemRows];
                        next[idx].quantity = parseInt(e.target.value, 10);
                        setOrderItemRows(next);
                      }}
                      className="w-16 bg-slate-900 border border-slate-700 text-slate-100 rounded-lg p-1.5 font-mono text-xs"
                    />
                  </div>
                ))}
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button onClick={() => setOrderModalOpen(false)} className="px-3 py-1.5 bg-slate-800 text-slate-300 rounded-lg text-xs">
                Cancel
              </button>
              <button
                onClick={() =>
                  createOrderMutation.mutate({
                    order_number: orderNum,
                    warehouse_id: activeWarehouseId!,
                    customer_name: custName,
                    destination_address: destAddr,
                    customer_lat: parseFloat(destLat),
                    customer_lon: parseFloat(destLon),
                    promised_at: new Date(Date.now() + parseInt(promisedHours, 10) * 3600000).toISOString(),
                    priority: orderPriority,
                    items: orderItemRows,
                  })
                }
                className="px-4 py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-semibold"
              >
                Create Order
              </button>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
