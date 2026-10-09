import React, { useState } from 'react';
import { Menu, Bell, X } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { Sidebar } from './Sidebar';
import { getRoleCode } from '../../types/api';

interface HeaderProps {
  onMenuClick?: () => void;
  title?: string;
}

export function Header({ onMenuClick, title }: HeaderProps) {
  const { user } = useAuth();

  return (
    <header
      className="flex items-center justify-between h-14 px-4 border-b border-line bg-[#14171C]/80 backdrop-blur-md sticky top-0 z-30"
      role="banner"
    >
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuClick}
          className="btn-ghost p-2 lg:hidden"
          aria-label="Open navigation menu"
        >
          <Menu size={20} />
        </button>
        {title && <h1 className="section-title hidden sm:block">{title}</h1>}
      </div>

      <div className="flex items-center gap-2">
        <button className="btn-ghost p-2 relative" aria-label="Notifications">
          <Bell size={18} />
        </button>
        {user && (
          <div className="flex items-center gap-2 pl-2 border-l border-line">
            <div className="w-7 h-7 rounded-full bg-grad-lead flex items-center justify-center text-white text-xs font-medium">
              {user.full_name?.charAt(0).toUpperCase()}
            </div>
            <span className="caption hidden sm:block font-mono text-[11px] capitalize">{getRoleCode(user.role).replace('_', ' ')}</span>
          </div>
        )}
      </div>
    </header>
  );
}

export function AppShell({ children, title }: { children: React.ReactNode; title?: string }) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden bg-[#0F1216]">
      {/* Desktop sidebar */}
      <div className="hidden lg:flex lg:w-56 lg:flex-shrink-0">
        <Sidebar />
      </div>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 flex lg:hidden">
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
          />
          <div className="relative z-50 w-56 flex flex-col">
            <Sidebar onClose={() => setMobileOpen(false)} />
          </div>
          <button
            className="absolute top-3 right-3 z-50 p-2 rounded-btn bg-surface text-ink-mute"
            onClick={() => setMobileOpen(false)}
            aria-label="Close menu"
          >
            <X size={18} />
          </button>
        </div>
      )}

      {/* Main area */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <Header onMenuClick={() => setMobileOpen(true)} title={title} />
        <main className="flex-1 overflow-y-auto p-4 lg:p-6" id="main-content">
          {children}
        </main>
      </div>
    </div>
  );
}
