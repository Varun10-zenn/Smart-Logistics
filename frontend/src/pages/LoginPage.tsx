import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Shield, 
  Lock, 
  Mail, 
  Eye, 
  EyeOff, 
  ArrowRight,
  Activity,
  User as UserIcon,
  ShoppingBag
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { getRoleCode } from '../types/api';

interface LoginPageProps {
  type: 'customer-login' | 'customer-register' | 'staff-login';
}

export function LoginPage({ type }: LoginPageProps) {
  const { login, register, logout } = useAuth();
  const navigate = useNavigate();

  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setIsSubmitting(true);

    try {
      if (type === 'customer-register') {
        await register({ username, email, password });
      } else {
        await login(email, password);
      }

      const userStr = sessionStorage.getItem('user');
      const user = userStr ? JSON.parse(userStr) : null;
      const roleCode = getRoleCode(user?.role);

      if (type === 'staff-login') {
        if (roleCode === 'customer') {
          await logout();
          setErrorMsg('This is a customer account, use the shop');
          setIsSubmitting(false);
          return;
        }
        if (roleCode === 'warehouse_operator') {
          navigate('/picker');
        } else if (roleCode === 'driver') {
          navigate('/rider');
        } else {
          navigate('/dashboard');
        }
      } else {
        // customer-login or customer-register
        if (roleCode !== 'customer') {
          await logout();
          setErrorMsg('Use the staff login');
          setIsSubmitting(false);
          return;
        }
        navigate('/shop');
      }
    } catch (err: any) {
      console.error(err);
      const msg =
        err.response?.data?.error?.message ||
        err.response?.data?.detail?.message ||
        err.response?.data?.detail ||
        (type === 'customer-register' ? 'Registration failed. Username or email may already be registered.' : 'Authentication failed. Invalid credentials.');
      setErrorMsg(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setIsSubmitting(false);
    }
  };

  const isCustomerFlow = type === 'customer-login' || type === 'customer-register';

  return (
    <div className="min-h-screen bg-[#0B0F17] text-slate-100 flex flex-col justify-between selection:bg-indigo-500 selection:text-white font-sans relative overflow-hidden">
      {/* Background Decorative Gradients */}
      <div className="absolute top-0 left-1/4 w-[600px] h-[600px] bg-indigo-900/20 blur-[140px] rounded-full pointer-events-none" />
      <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-sky-900/15 blur-[120px] rounded-full pointer-events-none" />

      {/* Top Navbar Header */}
      <header className="px-6 py-5 flex items-center justify-between border-b border-slate-800/80 backdrop-blur-md bg-[#0B0F17]/80 z-10">
        <div className="flex items-center gap-3 cursor-pointer" onClick={() => navigate('/')}>
          <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-indigo-500 to-sky-400 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Activity className="text-white" size={20} />
          </div>
          <div>
            <h1 className="font-serif text-lg tracking-tight font-medium text-white">Meridian</h1>
            <p className="text-[11px] text-slate-400 -mt-1 tracking-wider uppercase">Logistics Platform</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/')}
            className="text-xs text-slate-400 hover:text-white transition-colors"
          >
            ← Home
          </button>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-slate-800 bg-slate-900/60 text-xs text-slate-300">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>{isCustomerFlow ? 'Storefront Portal' : 'Staff Portal'}</span>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 flex items-center justify-center p-4 sm:p-6 lg:p-8 z-10">
        <div className="w-full max-w-md">
          <div className="card p-6 sm:p-8 bg-[#121824]/90 border border-slate-800/90 rounded-2xl shadow-2xl backdrop-blur-xl space-y-6">
            
            {/* Header info */}
            <div className="space-y-1 text-center">
              <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center mx-auto mb-3">
                {isCustomerFlow ? <ShoppingBag size={24} /> : <Shield size={24} />}
              </div>
              <h3 className="text-xl font-serif text-white">
                {type === 'customer-register'
                  ? 'Customer Registration'
                  : type === 'customer-login'
                  ? 'Customer Login'
                  : 'Staff Access Portal'}
              </h3>
              <p className="text-xs text-slate-400">
                {type === 'customer-register'
                  ? 'Create an account to shop from nearby darkstores.'
                  : type === 'customer-login'
                  ? 'Sign in to your customer account to place & track orders.'
                  : 'Sign in with your staff account (Admin, Picker, Driver).'}
              </p>
            </div>

            {errorMsg && (
              <div className="p-3 rounded-lg border border-red-500/30 bg-red-500/10 text-red-300 text-xs flex items-start gap-2">
                <span className="font-bold">Error:</span>
                <span>{errorMsg}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Username Input (Customer Register Mode) */}
              {type === 'customer-register' && (
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-slate-300">Username</label>
                  <div className="relative">
                    <UserIcon size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
                    <input
                      type="text"
                      required
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      placeholder="john_doe"
                      className="w-full bg-slate-900/80 border border-slate-700/80 focus:border-indigo-500 rounded-xl py-2.5 pl-10 pr-4 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-colors"
                    />
                  </div>
                </div>
              )}

              {/* Email Input */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300">Email Address</label>
                <div className="relative">
                  <Mail size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder={isCustomerFlow ? 'customer@example.com' : 'staff@smartlogistics.com'}
                    className="w-full bg-slate-900/80 border border-slate-700/80 focus:border-indigo-500 rounded-xl py-2.5 pl-10 pr-4 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-colors"
                  />
                </div>
              </div>

              {/* Password Input */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300">Password</label>
                <div className="relative">
                  <Lock size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full bg-slate-900/80 border border-slate-700/80 focus:border-indigo-500 rounded-xl py-2.5 pl-10 pr-10 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-colors"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full mt-2 py-3 px-4 bg-gradient-to-r from-indigo-600 to-sky-500 hover:from-indigo-500 hover:to-sky-400 text-white text-sm font-semibold rounded-xl shadow-lg shadow-indigo-600/25 flex items-center justify-center gap-2 disabled:opacity-50 transition-all duration-200 cursor-pointer"
              >
                {isSubmitting ? (
                  <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <>
                    <span>
                      {type === 'customer-register'
                        ? 'Register Customer Account'
                        : type === 'customer-login'
                        ? 'Sign In to Shop'
                        : 'Staff Sign In'}
                    </span>
                    <ArrowRight size={16} />
                  </>
                )}
              </button>
            </form>

            {/* Links Section */}
            <div className="pt-2 text-center text-xs text-slate-400 border-t border-slate-800/80 space-y-2">
              {type === 'customer-login' && (
                <p>
                  Don't have a customer account?{' '}
                  <button
                    onClick={() => navigate('/shop/register')}
                    className="text-indigo-400 font-semibold hover:underline"
                  >
                    Register here
                  </button>
                </p>
              )}
              {type === 'customer-register' && (
                <p>
                  Already have an account?{' '}
                  <button
                    onClick={() => navigate('/shop/login')}
                    className="text-indigo-400 font-semibold hover:underline"
                  >
                    Sign in here
                  </button>
                </p>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="px-6 py-4 border-t border-slate-800/60 text-center text-xs text-slate-400 z-10">
        © 2026 Meridian Smart Logistics Platform. All Rights Reserved.
      </footer>
    </div>
  );
}
