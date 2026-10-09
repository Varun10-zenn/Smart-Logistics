
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Warehouse,
  Truck,
  ShieldAlert,
  Zap,
  Brain,
  LogOut,
  Activity,
  ShoppingBag,
  Clock,
  PackageCheck,
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';

import { getRoleCode } from '../../types/api';

interface NavItem {
  to: string;
  icon: React.ReactNode;
  label: string;
  roles?: string[];
}

const navItems: NavItem[] = [
  { to: '/shop', icon: <ShoppingBag size={18} />, label: 'Customer Shop', roles: ['customer', 'admin'] },
  { to: '/shop/orders', icon: <Clock size={18} />, label: 'My Orders', roles: ['customer', 'admin'] },
  { to: '/picker', icon: <PackageCheck size={18} />, label: 'Mobile Picker App', roles: ['warehouse_operator', 'admin'] },
  { to: '/dashboard', icon: <LayoutDashboard size={18} />, label: 'Dashboard', roles: ['admin', 'fleet_manager', 'station_admin'] },
  { to: '/warehouse', icon: <Warehouse size={18} />, label: 'Warehouse Management', roles: ['admin', 'warehouse_operator', 'fleet_manager'] },
  { to: '/deliveries', icon: <Truck size={18} />, label: 'Deliveries', roles: ['admin', 'fleet_manager', 'driver'] },
  { to: '/safety', icon: <ShieldAlert size={18} />, label: 'Safety', roles: ['admin', 'fleet_manager', 'driver'] },
  { to: '/charging', icon: <Zap size={18} />, label: 'EV Charging', roles: ['admin', 'fleet_manager', 'driver', 'station_admin'] },
  { to: '/ai-insights', icon: <Brain size={18} />, label: 'AI Insights', roles: ['admin', 'fleet_manager'] },
];

interface SidebarProps {
  collapsed?: boolean;
  onClose?: () => void;
}

export function Sidebar({ collapsed = false, onClose }: SidebarProps) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const role = getRoleCode(user?.role);

  const visibleItems = navItems.filter(
    (item) => !item.roles || item.roles.includes(role),
  );

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <nav
      className="flex flex-col h-full bg-grad-side border-r border-line/50"
      aria-label="Main navigation"
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 pt-5 pb-4 border-b border-line/30">
        <div className="p-2 rounded-btn bg-white/10">
          <Activity size={18} className="text-white" />
        </div>
        {!collapsed && (
          <div>
            <p className="font-serif text-[15px] text-white leading-tight">Meridian</p>
            <p className="caption text-white/40 text-[11px]">Logistics Platform</p>
          </div>
        )}
      </div>

      {/* Nav links */}
      <div className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
        {visibleItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            onClick={onClose}
            className={({ isActive }) =>
              isActive ? 'sidebar-item-active' : 'sidebar-item'
            }
          >
            {item.icon}
            {!collapsed && <span>{item.label}</span>}
          </NavLink>
        ))}
      </div>

      {/* User + logout */}
      <div className="border-t border-line/30 p-3 space-y-1">
        {!collapsed && user && (
          <div className="px-3 py-2">
            <p className="text-[13px] text-ink font-medium truncate">{user.full_name}</p>
            <p className="caption truncate capitalize">{role.replace('_', ' ')}</p>
          </div>
        )}
        <button
          onClick={handleLogout}
          className="sidebar-item w-full text-left"
          aria-label="Log out"
        >
          <LogOut size={18} />
          {!collapsed && <span>Log out</span>}
        </button>
      </div>
    </nav>
  );
}
