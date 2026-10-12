import type { ClientStatus } from '../lib/types';

const styles: Record<ClientStatus, { label: string; className: string }> = {
  booked: { label: 'Booked', className: 'bg-green-100 text-green-700' },
  negotiating: { label: 'AI Negotiating', className: 'bg-yellow-100 text-yellow-700' },
  due: { label: 'Due for Outreach', className: 'bg-blue-100 text-blue-700' },
  paused: { label: 'Paused / Manual', className: 'bg-amber-100 text-amber-800' },
  opted_out: { label: 'Opted Out', className: 'bg-red-100 text-red-700' },
  idle: { label: 'Idle', className: 'bg-gray-100 text-gray-700' },
};

export default function StatusBadge({ status, small = false }: { status: ClientStatus; small?: boolean }) {
  const { label, className } = styles[status];
  return (
    <span className={`${small ? 'text-[10px] px-2 py-0.5 rounded' : 'text-xs px-2.5 py-1 rounded-full'} font-semibold ${className}`}>
      {label}
    </span>
  );
}
