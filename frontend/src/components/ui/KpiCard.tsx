import React from 'react';

interface KpiCardProps {
  label: string;
  value: string | number;
  sub?: string;
  lead?: boolean;
  icon?: React.ReactNode;
  trend?: { value: string; up?: boolean };
}

export function KpiCard({ label, value, sub, lead = false, icon, trend }: KpiCardProps) {
  if (lead) {
    return (
      <div className="relative overflow-hidden rounded-card p-5 bg-grad-lead shadow-card flex flex-col gap-2 min-h-[120px]">
        <div className="absolute inset-0 opacity-10 pointer-events-none">
          <div className="absolute -right-8 -top-8 w-32 h-32 rounded-full border border-white/20" />
          <div className="absolute -right-4 -top-4 w-20 h-20 rounded-full border border-white/10" />
        </div>
        <p className="caption uppercase tracking-widest text-white/60 z-10">{label}</p>
        <p className="kpi-number-lead z-10">{value}</p>
        {sub && <p className="caption text-white/50 z-10">{sub}</p>}
        {trend && (
          <span className={`caption z-10 ${trend.up ? 'text-[#88A594]' : 'text-[#C58783]'}`}>
            {trend.up ? '↑' : '↓'} {trend.value}
          </span>
        )}
      </div>
    );
  }

  return (
    <div className="card p-5 flex flex-col gap-2 hover:shadow-card-hover transition-shadow">
      <div className="flex items-center justify-between">
        <p className="caption uppercase tracking-widest text-ink-mute">{label}</p>
        {icon && <span className="text-ink-mute/60">{icon}</span>}
      </div>
      <p className="kpi-number">{value}</p>
      {sub && <p className="caption">{sub}</p>}
      {trend && (
        <span className={`caption ${trend.up ? 'text-[#88A594]' : 'text-[#C58783]'}`}>
          {trend.up ? '↑' : '↓'} {trend.value}
        </span>
      )}
    </div>
  );
}
