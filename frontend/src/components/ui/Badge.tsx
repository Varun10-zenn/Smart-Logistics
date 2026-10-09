import { CheckCircle, AlertTriangle, XCircle, Info } from 'lucide-react';

type BadgeVariant = 'ok' | 'warn' | 'critical' | 'info' | 'neutral';

interface BadgeProps {
  variant: BadgeVariant;
  label: string;
  icon?: boolean;
}

const icons: Record<BadgeVariant, JSX.Element | null> = {
  ok: <CheckCircle size={11} />,
  warn: <AlertTriangle size={11} />,
  critical: <XCircle size={11} />,
  info: <Info size={11} />,
  neutral: null,
};

export function Badge({ variant, label, icon = true }: BadgeProps) {
  const cls =
    variant === 'ok'
      ? 'badge-ok'
      : variant === 'warn'
        ? 'badge-warn'
        : variant === 'critical'
          ? 'badge-critical'
          : variant === 'info'
            ? 'badge-info'
            : 'badge-neutral';

  return (
    <span className={cls}>
      {icon && icons[variant]}
      {label}
    </span>
  );
}

// Maps backend status strings to badge variants
export function statusToBadge(status: string): BadgeVariant {
  const s = status.toLowerCase();
  if (['operational', 'available', 'completed', 'active', 'healthy', 'connected'].some((v) => s.includes(v))) return 'ok';
  if (['charging', 'in_transit', 'dispatched', 'assigned', 'reserved', 'confirmed'].some((v) => s.includes(v))) return 'info';
  if (['warning', 'degraded', 'low', 'medium'].some((v) => s.includes(v))) return 'warn';
  if (['critical', 'failed', 'fault', 'offline', 'high'].some((v) => s.includes(v))) return 'critical';
  return 'neutral';
}

export function StatusBadge({ status }: { status: string }) {
  return <Badge variant={statusToBadge(status)} label={status.replace(/_/g, ' ')} />;
}

export function SeverityBadge({ severity }: { severity: string }) {
  const s = severity.toLowerCase();
  const variant: BadgeVariant = s === 'high' || s === 'critical' ? 'critical' : s === 'medium' ? 'warn' : 'info';
  return <Badge variant={variant} label={severity} />;
}
