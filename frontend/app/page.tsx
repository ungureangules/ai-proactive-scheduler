'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { TrendingUp, Users, CalendarCheck, Send } from 'lucide-react';
import { api, useBusiness } from '../src/lib/api';
import { formatDateTime } from '../src/lib/format';
import type { Appointment, Dashboard as DashboardData } from '../src/lib/types';

const sourceLabels: Record<Appointment['source'], { label: string; className: string }> = {
  ai: { label: 'AI Booked', className: 'bg-green-100 text-green-700' },
  google: { label: 'Google Calendar', className: 'bg-blue-100 text-blue-700' },
  manual: { label: 'Added Manually', className: 'bg-purple-100 text-purple-700' },
};

export default function Dashboard() {
  const { data: business } = useBusiness();
  const { data, isLoading, isError } = useQuery({
    queryKey: ['dashboard'],
    queryFn: async () => (await api.get<DashboardData>('/dashboard/')).data,
  });

  const metrics = [
    { title: "Upcoming Appointments", value: data?.upcoming_appointments, icon: CalendarCheck, color: "text-blue-600", bg: "bg-blue-100" },
    { title: "AI Bookings (30 days)", value: data?.ai_bookings_30d, icon: TrendingUp, color: "text-green-600", bg: "bg-green-100" },
    { title: "Active Clients (6 months)", value: data?.active_clients, icon: Users, color: "text-purple-600", bg: "bg-purple-100" },
    {
      title: "Outreach Conversion (30 days)",
      value: data ? (data.conversion_rate_30d === null ? '—' : `${Math.round(data.conversion_rate_30d * 100)}%`) : undefined,
      hint: data ? `${data.outreach_sent_30d} AI messages sent` : undefined,
      icon: Send,
      color: "text-orange-600",
      bg: "bg-orange-100",
    },
  ];

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500">Welcome back! Here&apos;s what&apos;s happening with your AI assistant.</p>
      </header>

      {isError && <p className="mb-6 text-sm text-red-600">Could not load the dashboard. Is the API running?</p>}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
        {metrics.map((metric) => (
          <div key={metric.title} className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
            <div className="flex items-center justify-between mb-4">
              <div className={`${metric.bg} p-3 rounded-lg`}>
                <metric.icon className={`w-6 h-6 ${metric.color}`} />
              </div>
            </div>
            <h3 className="text-gray-500 text-sm font-medium">{metric.title}</h3>
            <p className="text-2xl font-bold text-gray-900">{metric.value ?? (isLoading ? '…' : '—')}</p>
            {metric.hint && <p className="text-xs text-gray-400 mt-1">{metric.hint}</p>}
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="font-bold text-gray-900 text-lg">Upcoming Appointments</h2>
          <Link href="/calendar" className="text-blue-600 text-sm font-medium hover:underline">View All</Link>
        </div>
        {data && data.upcoming.length === 0 ? (
          <p className="px-6 py-10 text-center text-sm text-gray-500">
            No upcoming appointments yet. Connect Google Calendar in <Link href="/settings" className="text-blue-600 hover:underline">Settings</Link> to import your schedule.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
                  <th className="px-6 py-3 font-semibold">Client</th>
                  <th className="px-6 py-3 font-semibold">Service</th>
                  <th className="px-6 py-3 font-semibold">Date & Time</th>
                  <th className="px-6 py-3 font-semibold">Source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 text-sm">
                {data?.upcoming.map((app) => (
                  <tr key={app.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4 font-medium text-gray-900">{app.client_name}</td>
                    <td className="px-6 py-4 text-gray-600">{app.service_type ?? '—'}</td>
                    <td className="px-6 py-4 text-gray-600">{formatDateTime(app.start_time, business?.timezone)}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${sourceLabels[app.source].className}`}>
                        {sourceLabels[app.source].label}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
