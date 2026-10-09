import React from 'react';
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  useNavigate,
} from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ShoppingBag, Shield, Activity, ArrowRight } from 'lucide-react';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { LoginPage } from './pages/LoginPage';
import { ShopPage } from './pages/ShopPage';
import { OrderTrackingPage } from './pages/OrderTrackingPage';
import { PickerPage } from './pages/PickerPage';
import { AccessDeniedPage } from './pages/AccessDeniedPage';
import { DashboardPage } from './pages/DashboardPage';
import { WarehousePage } from './pages/WarehousePage';
import { DeliveriesPage } from './pages/DeliveriesPage';
import { DeliveryDetailPage } from './pages/DeliveryDetailPage';
import { SafetyPage } from './pages/SafetyPage';
import { ChargingPage } from './pages/ChargingPage';
import { ChargingOptimizePage } from './pages/ChargingOptimizePage';
import { AIInsightsPage } from './pages/AIInsightsPage';
import { RiderPage } from './pages/RiderPage';
import { getRoleCode } from './types/api';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function LoadingScreen() {
  return (
    <div className="min-h-screen bg-[#0B0F17] flex items-center justify-center text-slate-300 font-sans">
      <div className="flex items-center gap-3">
        <div className="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        <span className="text-sm font-medium">Authenticating session...</span>
      </div>
    </div>
  );
}

function RoleGuard({ allowedRoles, fallbackLoginPath, children }: { allowedRoles: string[]; fallbackLoginPath: string; children: React.ReactNode }) {
  const { user, isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <LoadingScreen />;
  }

  if (!isAuthenticated) {
    return <Navigate to={fallbackLoginPath} replace />;
  }

  const roleCode = getRoleCode(user?.role);
  if (allowedRoles.length > 0 && !allowedRoles.includes(roleCode)) {
    return <AccessDeniedPage />;
  }

  return <>{children}</>;
}

function PublicOnlyRoute({ fallbackPath, children }: { fallbackPath?: string; children: React.ReactNode }) {
  const { user, isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <LoadingScreen />;
  }

  if (isAuthenticated) {
    const roleCode = getRoleCode(user?.role);
    if (fallbackPath) {
      return <Navigate to={fallbackPath} replace />;
    }
    if (roleCode === 'customer') {
      return <Navigate to="/shop" replace />;
    } else if (roleCode === 'warehouse_operator') {
      return <Navigate to="/picker" replace />;
    } else if (roleCode === 'driver') {
      return <Navigate to="/rider" replace />;
    } else {
      return <Navigate to="/dashboard" replace />;
    }
  }

  return <>{children}</>;
}

function LandingPage() {
  const navigate = useNavigate();
  return (
    <div className="min-h-screen bg-[#0B0F17] text-slate-100 flex flex-col justify-between font-sans relative overflow-hidden">
      {/* Background Decorative Gradients */}
      <div className="absolute top-0 left-1/4 w-[600px] h-[600px] bg-indigo-900/20 blur-[140px] rounded-full pointer-events-none" />
      <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-emerald-900/15 blur-[120px] rounded-full pointer-events-none" />

      {/* Header */}
      <header className="px-6 py-5 flex items-center justify-between border-b border-slate-800/80 backdrop-blur-md bg-[#0B0F17]/80 z-10">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-indigo-500 to-sky-400 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Activity className="text-white" size={20} />
          </div>
          <div>
            <h1 className="font-serif text-lg tracking-tight font-medium text-white">Meridian</h1>
            <p className="text-[11px] text-slate-400 -mt-1 tracking-wider uppercase">Logistics Platform</p>
          </div>
        </div>
      </header>

      {/* Hero Content */}
      <main className="flex-1 flex items-center justify-center p-6 z-10">
        <div className="max-w-2xl w-full text-center space-y-8">
          <div className="space-y-3">
            <span className="px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold uppercase tracking-wider">
              Dual Entry Portals
            </span>
            <h2 className="text-4xl sm:text-5xl font-serif text-white tracking-tight leading-tight">
              Welcome to Meridian Logistics
            </h2>
            <p className="text-sm sm:text-base text-slate-400 max-w-lg mx-auto leading-relaxed">
              Choose your portal below to enter as a Customer for instant grocery fulfillment or as Operations Staff.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-lg mx-auto">
            {/* Customer Button */}
            <button
              onClick={() => navigate('/shop/login')}
              className="p-6 rounded-2xl bg-[#121824] border border-emerald-500/30 hover:border-emerald-500/80 hover:bg-emerald-950/20 transition-all text-left group shadow-xl flex flex-col justify-between cursor-pointer"
            >
              <div className="space-y-3">
                <div className="w-12 h-12 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
                  <ShoppingBag size={24} />
                </div>
                <div>
                  <h3 className="text-lg font-serif text-white font-semibold flex items-center gap-1.5">
                    <span>Shop as Customer</span>
                    <ArrowRight size={16} className="text-emerald-400 group-hover:translate-x-1 transition-transform" />
                  </h3>
                  <p className="text-xs text-slate-400 mt-1">Browse products, place instant orders & track live status.</p>
                </div>
              </div>
            </button>

            {/* Staff Button */}
            <button
              onClick={() => navigate('/staff/login')}
              className="p-6 rounded-2xl bg-[#121824] border border-indigo-500/30 hover:border-indigo-500/80 hover:bg-indigo-950/20 transition-all text-left group shadow-xl flex flex-col justify-between cursor-pointer"
            >
              <div className="space-y-3">
                <div className="w-12 h-12 rounded-xl bg-indigo-500/20 text-indigo-400 flex items-center justify-center">
                  <Shield size={24} />
                </div>
                <div>
                  <h3 className="text-lg font-serif text-white font-semibold flex items-center gap-1.5">
                    <span>Staff Login</span>
                    <ArrowRight size={16} className="text-indigo-400 group-hover:translate-x-1 transition-transform" />
                  </h3>
                  <p className="text-xs text-slate-400 mt-1">Access Admin dashboard, Picker mobile screen or Rider app.</p>
                </div>
              </div>
            </button>
          </div>
        </div>
      </main>

      <footer className="px-6 py-4 border-t border-slate-800/60 text-center text-xs text-slate-400 z-10">
        © 2026 Meridian Smart Logistics Platform. All Rights Reserved.
      </footer>
    </div>
  );
}



export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            {/* Landing Entry Page */}
            <Route path="/" element={<LandingPage />} />

            {/* Entry Point 1: /shop/login */}
            <Route
              path="/shop/login"
              element={
                <PublicOnlyRoute fallbackPath="/shop">
                  <LoginPage type="customer-login" />
                </PublicOnlyRoute>
              }
            />

            {/* Entry Point 2: /shop/register */}
            <Route
              path="/shop/register"
              element={
                <PublicOnlyRoute fallbackPath="/shop">
                  <LoginPage type="customer-register" />
                </PublicOnlyRoute>
              }
            />

            {/* Entry Point 3: /staff/login */}
            <Route
              path="/staff/login"
              element={
                <PublicOnlyRoute>
                  <LoginPage type="staff-login" />
                </PublicOnlyRoute>
              }
            />

            {/* Redirect old /login to /staff/login */}
            <Route path="/login" element={<Navigate to="/staff/login" replace />} />

            {/* Customer Shop & Tracking Routes (Customer Only) */}
            <Route
              path="/shop"
              element={
                <RoleGuard allowedRoles={['customer']} fallbackLoginPath="/shop/login">
                  <ShopPage />
                </RoleGuard>
              }
            />
            <Route
              path="/shop/orders"
              element={
                <RoleGuard allowedRoles={['customer']} fallbackLoginPath="/shop/login">
                  <OrderTrackingPage />
                </RoleGuard>
              }
            />
            <Route
              path="/shop/orders/:id"
              element={
                <RoleGuard allowedRoles={['customer']} fallbackLoginPath="/shop/login">
                  <OrderTrackingPage />
                </RoleGuard>
              }
            />

            {/* Picker Mobile App Route */}
            <Route
              path="/picker"
              element={
                <RoleGuard allowedRoles={['warehouse_operator', 'admin']} fallbackLoginPath="/staff/login">
                  <PickerPage />
                </RoleGuard>
              }
            />
            {/* Rider Route */}
            <Route
              path="/rider"
              element={
                <RoleGuard allowedRoles={['driver', 'admin']} fallbackLoginPath="/staff/login">
                  <RiderPage />
                </RoleGuard>
              }
            />

            {/* Admin & Operations Routes */}
            <Route
              path="/dashboard"
              element={
                <RoleGuard allowedRoles={['admin', 'fleet_manager', 'station_admin']} fallbackLoginPath="/staff/login">
                  <DashboardPage />
                </RoleGuard>
              }
            />
            <Route
              path="/warehouse"
              element={
                <RoleGuard allowedRoles={['admin', 'warehouse_operator', 'fleet_manager']} fallbackLoginPath="/staff/login">
                  <WarehousePage />
                </RoleGuard>
              }
            />
            <Route
              path="/deliveries"
              element={
                <RoleGuard allowedRoles={['admin', 'fleet_manager', 'driver']} fallbackLoginPath="/staff/login">
                  <DeliveriesPage />
                </RoleGuard>
              }
            />
            <Route
              path="/deliveries/:id"
              element={
                <RoleGuard allowedRoles={['admin', 'fleet_manager', 'driver']} fallbackLoginPath="/staff/login">
                  <DeliveryDetailPage />
                </RoleGuard>
              }
            />
            <Route
              path="/safety"
              element={
                <RoleGuard allowedRoles={['admin', 'fleet_manager', 'driver']} fallbackLoginPath="/staff/login">
                  <SafetyPage />
                </RoleGuard>
              }
            />
            <Route
              path="/charging"
              element={
                <RoleGuard allowedRoles={['admin', 'fleet_manager', 'driver', 'station_admin']} fallbackLoginPath="/staff/login">
                  <ChargingPage />
                </RoleGuard>
              }
            />
            <Route
              path="/charging/optimize"
              element={
                <RoleGuard allowedRoles={['admin', 'fleet_manager', 'driver', 'station_admin']} fallbackLoginPath="/staff/login">
                  <ChargingOptimizePage />
                </RoleGuard>
              }
            />
            <Route
              path="/ai-insights"
              element={
                <RoleGuard allowedRoles={['admin', 'fleet_manager']} fallbackLoginPath="/staff/login">
                  <AIInsightsPage />
                </RoleGuard>
              }
            />

            {/* Catch-all */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
