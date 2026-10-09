import { useNavigate } from 'react-router-dom';
import { ShieldAlert, ArrowLeft, LogOut, ShoppingBag } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { getRoleCode } from '../types/api';

export function AccessDeniedPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const roleCode = getRoleCode(user?.role);
  const isCustomer = roleCode === 'customer';

  const getHomePath = () => {
    if (roleCode === 'customer') return '/shop';
    if (roleCode === 'warehouse_operator') return '/picker';
    if (roleCode === 'driver') return '/rider';
    return '/dashboard';
  };

  const handleLogout = async () => {
    await logout();
    navigate(isCustomer ? '/shop/login' : '/staff/login');
  };

  return (
    <div className="min-h-screen bg-[#0B0F17] flex items-center justify-center p-4 text-slate-100 font-sans">
      <div className="max-w-md w-full bg-[#121824] border border-slate-800 rounded-2xl p-6 sm:p-8 text-center space-y-6 shadow-2xl">
        <div className="w-14 h-14 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center mx-auto">
          {isCustomer ? <ShoppingBag size={28} /> : <ShieldAlert size={28} />}
        </div>

        <div className="space-y-2">
          <h1 className="text-2xl font-serif text-white">
            {isCustomer ? 'Access Denied' : 'Staff Access Required'}
          </h1>
          <p className="text-xs text-slate-400 leading-relaxed">
            {isCustomer ? (
              <>
                You are signed in as a <span className="text-emerald-400 font-medium capitalize">Customer</span>. This admin or staff page is restricted. Please return to the shop storefront.
              </>
            ) : (
              <>
                You are signed in as staff (<span className="text-indigo-400 font-medium capitalize">{roleCode.replace('_', ' ')}</span>). This page is restricted or intended for customer storefront view.
              </>
            )}
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
          <button
            onClick={() => navigate(getHomePath())}
            className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl flex items-center justify-center gap-2 transition-colors cursor-pointer"
          >
            <ArrowLeft size={16} />
            <span>{isCustomer ? 'Return to Shop (/shop)' : 'Go to Staff Portal'}</span>
          </button>
          <button
            onClick={handleLogout}
            className="w-full py-2.5 px-4 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-xl flex items-center justify-center gap-2 transition-colors cursor-pointer"
          >
            <LogOut size={16} />
            <span>Log Out</span>
          </button>
        </div>
      </div>
    </div>
  );
}
