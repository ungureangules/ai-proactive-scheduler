'use client';

import React, { useMemo, useState } from 'react';
import Link from 'next/link';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Calendar as CalendarIcon, RefreshCw, ChevronLeft, ChevronRight, Plus } from 'lucide-react';
import { api, errorMessage, useBusiness, useIntegrations } from '../../src/lib/api';
import { dateKey, formatDateTime, formatTime, relativeTime } from '../../src/lib/format';
import { useNow } from '../../src/lib/useNow';
import Modal, { inputClass, labelClass, primaryButton, secondaryButton } from '../../src/components/Modal';
import type { Appointment, Client } from '../../src/lib/types';

const daysOfWeek = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const DAY_MS = 86_400_000;

const sourceStyles: Record<Appointment['source'], string> = {
  google: 'bg-blue-50 text-blue-700 border border-blue-100',
  ai: 'bg-green-50 text-green-700 border border-green-100',
  manual: 'bg-purple-50 text-purple-700 border border-purple-100',
};

function monthGrid(year: number, month: number) {
  const offset = new Date(Date.UTC(year, month, 1)).getUTCDay();
  const daysInMonth = new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
  const count = Math.ceil((offset + daysInMonth) / 7) * 7;
  return Array.from({ length: count }, (_, i) => {
    const date = new Date(Date.UTC(year, month, 1 - offset + i));
    return { key: date.toISOString().slice(0, 10), day: date.getUTCDate(), currentMonth: date.getUTCMonth() === month, time: date.getTime() };
  });
}

export default function CalendarPage() {
  const queryClient = useQueryClient();
  const now = useNow();
  const { data: business } = useBusiness();
  const { data: integrations } = useIntegrations();
  const tz = business?.timezone;
  const [month, setMonth] = useState(() => {
    const today = new Date();
    return { year: today.getFullYear(), month: today.getMonth() };
  });
  const [adding, setAdding] = useState<string | null>(null); // date key to prefill, '' for none
  const [selected, setSelected] = useState<Appointment | null>(null);
  const [syncMessage, setSyncMessage] = useState('');

  const days = useMemo(() => monthGrid(month.year, month.month), [month]);
  // Fetch a day of margin on both sides; events are bucketed by their date in the business timezone
  const rangeStart = new Date(days[0].time - DAY_MS).toISOString();
  const rangeEnd = new Date(days[days.length - 1].time + 2 * DAY_MS).toISOString();

  const { data: appointments = [], isError } = useQuery({
    queryKey: ['appointments', rangeStart, rangeEnd],
    queryFn: async () =>
      (await api.get<Appointment[]>('/appointments/', { params: { start: rangeStart, end: rangeEnd } })).data,
  });

  const byDay = useMemo(() => {
    const map = new Map<string, Appointment[]>();
    for (const appointment of appointments) {
      const key = dateKey(new Date(appointment.start_time), tz);
      map.set(key, [...(map.get(key) ?? []), appointment]);
    }
    return map;
  }, [appointments, tz]);

  const sync = useMutation({
    mutationFn: async () => (await api.post<{ synced: number; skipped: number }>('/businesses/me/sync')).data,
    onSuccess: (result) => {
      setSyncMessage(
        `Synced ${result.synced} appointment${result.synced === 1 ? '' : 's'}` +
          (result.skipped ? `; ${result.skipped} event${result.skipped === 1 ? '' : 's'} had no matching client (add a phone number to the event description).` : '.'),
      );
      queryClient.invalidateQueries();
    },
    onError: (err) => setSyncMessage(errorMessage(err, 'Sync failed')),
  });

  const shiftMonth = (delta: number) =>
    setMonth(({ year, month: m }) => {
      const date = new Date(year, m + delta, 1);
      return { year: date.getFullYear(), month: date.getMonth() };
    });

  const todayKey = dateKey(new Date(now), tz);
  const monthLabel = new Date(month.year, month.month, 1).toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  const google = integrations?.google;

  return (
    <div className="p-8">
      <header className="mb-8 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Calendar</h1>
          <p className="text-gray-500">Track current and automatically negotiated bookings.</p>
        </div>
        <div className="flex gap-3">
          {google?.connected ? (
            <button onClick={() => sync.mutate()} disabled={sync.isPending} className={secondaryButton}>
              <RefreshCw className={`w-4 h-4 mr-2 ${sync.isPending ? 'animate-spin text-blue-600' : 'text-gray-500'}`} />
              {sync.isPending ? 'Syncing...' : 'Sync Google Calendar'}
            </button>
          ) : (
            <Link href="/settings" className={secondaryButton}>
              <CalendarIcon className="w-4 h-4 mr-2 text-gray-500" />
              Connect Google Calendar
            </Link>
          )}
          <button onClick={() => setAdding('')} className={primaryButton}>
            <Plus className="w-4 h-4 mr-2" />
            Add Booking
          </button>
        </div>
      </header>

      {syncMessage && <p className="mb-4 text-sm text-gray-600">{syncMessage}</p>}
      {isError && <p className="mb-4 text-sm text-red-600">Could not load appointments.</p>}

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-8">
        {/* Main Calendar Month View */}
        <div className="xl:col-span-3 bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-gray-900">{monthLabel}</h2>
            <div className="flex border border-gray-200 rounded-lg overflow-hidden">
              <button onClick={() => shiftMonth(-1)} aria-label="Previous month" className="p-2 hover:bg-gray-50 border-r border-gray-200 text-gray-600">
                <ChevronLeft className="w-5 h-5" />
              </button>
              <button onClick={() => shiftMonth(1)} aria-label="Next month" className="p-2 hover:bg-gray-50 text-gray-600">
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>
          </div>

          <div className="grid grid-cols-7 gap-px bg-gray-100 rounded-lg overflow-hidden">
            {/* Days of week header */}
            {daysOfWeek.map((day) => (
              <div key={day} className="bg-gray-50 text-gray-500 text-center py-2 text-xs font-semibold uppercase tracking-wider">
                {day}
              </div>
            ))}

            {/* Calendar squares */}
            {days.map((item) => {
              const isToday = item.key === todayKey;
              return (
                <div
                  key={item.key}
                  onDoubleClick={() => setAdding(item.key)}
                  className={`min-h-24 p-2 flex flex-col border border-gray-50 transition-colors ${
                    !item.currentMonth ? 'text-gray-300 bg-gray-50' : 'text-gray-700 bg-white hover:bg-gray-50/50'
                  } ${isToday ? 'ring-2 ring-blue-600 ring-inset' : ''}`}
                >
                  <span className={`text-sm font-medium p-1 w-6 h-6 flex items-center justify-center rounded-full ${
                    isToday ? 'bg-blue-600 text-white font-bold' : ''
                  }`}>
                    {item.day}
                  </span>
                  <div className="mt-2 space-y-1">
                    {byDay.get(item.key)?.map((ev) => (
                      <button
                        key={ev.id}
                        onClick={() => setSelected(ev)}
                        className={`w-full text-left text-[10px] p-1 rounded font-medium truncate ${sourceStyles[ev.source]}`}
                      >
                        <span className="font-semibold block">{formatTime(ev.start_time, tz)}</span>
                        {ev.service_type ? `${ev.service_type} (${ev.client_name})` : ev.client_name}
                      </button>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Sync Status Sidebar */}
        <div className="space-y-6">
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <h3 className="font-bold text-gray-900 text-lg mb-4 flex items-center">
              <CalendarIcon className="w-5 h-5 mr-2 text-blue-600" />
              Calendar Sync
            </h3>
            {google?.connected ? (
              <div className="space-y-4 text-sm">
                <div className="flex items-center justify-between gap-2 py-2 border-b border-gray-50">
                  <span className="text-gray-500">Connected Account</span>
                  <span className="font-medium text-gray-900 truncate">{google.account_email ?? '—'}</span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-gray-50">
                  <span className="text-gray-500">Calendar</span>
                  <span className="font-medium text-gray-900">{google.calendar_id === 'primary' ? 'Primary' : google.calendar_id}</span>
                </div>
                <div className="flex items-center justify-between py-2">
                  <span className="text-gray-500">Last Synced</span>
                  <span className="font-medium text-gray-900">{google.last_synced_at ? relativeTime(google.last_synced_at, now) : 'Never'}</span>
                </div>
              </div>
            ) : (
              <p className="text-sm text-gray-500">
                Not connected. <Link href="/settings" className="text-blue-600 hover:underline">Connect Google Calendar</Link> to import appointments and let the AI book into it.
              </p>
            )}
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <h3 className="font-bold text-gray-900 text-lg mb-4">Legend</h3>
            <div className="space-y-3 text-sm">
              <div className="flex items-center">
                <span className="w-3.5 h-3.5 rounded bg-blue-100 border border-blue-200 mr-2.5"></span>
                <span className="text-gray-600 font-medium">Google Calendar Sync</span>
              </div>
              <div className="flex items-center">
                <span className="w-3.5 h-3.5 rounded bg-green-100 border border-green-200 mr-2.5"></span>
                <span className="text-gray-600 font-medium">AI Booked</span>
              </div>
              <div className="flex items-center">
                <span className="w-3.5 h-3.5 rounded bg-purple-100 border border-purple-200 mr-2.5"></span>
                <span className="text-gray-600 font-medium">Added Manually</span>
              </div>
            </div>
            <p className="text-xs text-gray-400 mt-4">Double-click a day to add a booking.</p>
          </div>
        </div>
      </div>

      {adding !== null && <AddBookingModal defaultDate={adding || todayKey} onClose={() => setAdding(null)} />}
      {selected && <AppointmentModal appointment={selected} timeZone={tz} onClose={() => setSelected(null)} />}
    </div>
  );
}

function AddBookingModal({ defaultDate, onClose }: { defaultDate: string; onClose: () => void }) {
  const queryClient = useQueryClient();
  const { data: clients = [] } = useQuery({
    queryKey: ['clients', '', ''],
    queryFn: async () => (await api.get<Client[]>('/clients/')).data,
  });
  const [clientId, setClientId] = useState('');
  const [date, setDate] = useState(defaultDate);
  const [time, setTime] = useState('10:00');
  const [service, setService] = useState('');

  const create = useMutation({
    mutationFn: () =>
      api.post('/appointments/', { client_id: Number(clientId), date, time, service_type: service || null }),
    onSuccess: () => {
      queryClient.invalidateQueries();
      onClose();
    },
  });

  const selectedClient = clients.find((c) => String(c.id) === clientId);

  return (
    <Modal title="Add Booking" onClose={onClose}>
      {clients.length === 0 ? (
        <p className="text-sm text-gray-600">
          Add a client first on the <Link href="/clients" className="text-blue-600 hover:underline">Clients</Link> page.
        </p>
      ) : (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            create.mutate();
          }}
          className="space-y-4"
        >
          <div>
            <label className={labelClass} htmlFor="client">Client</label>
            <select
              id="client"
              required
              value={clientId}
              onChange={(e) => {
                setClientId(e.target.value);
                const picked = clients.find((c) => String(c.id) === e.target.value);
                if (picked?.last_service_type && !service) setService(picked.last_service_type);
              }}
              className={inputClass}
            >
              <option value="">Select a client…</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelClass} htmlFor="date">Date</label>
              <input id="date" type="date" required value={date} onChange={(e) => setDate(e.target.value)} className={inputClass} />
            </div>
            <div>
              <label className={labelClass} htmlFor="time">Time</label>
              <input id="time" type="time" required value={time} onChange={(e) => setTime(e.target.value)} className={inputClass} />
            </div>
          </div>
          <div>
            <label className={labelClass} htmlFor="service">Service</label>
            <input id="service" value={service} placeholder={selectedClient?.last_service_type ?? 'e.g. Haircut'} onChange={(e) => setService(e.target.value)} className={inputClass} />
          </div>
          {create.isError && <p className="text-sm text-red-600">{errorMessage(create.error)}</p>}
          <div className="flex justify-end gap-2">
            <button type="button" onClick={onClose} className={secondaryButton}>Cancel</button>
            <button type="submit" disabled={create.isPending} className={primaryButton}>
              {create.isPending ? 'Saving…' : 'Add Booking'}
            </button>
          </div>
        </form>
      )}
    </Modal>
  );
}

function AppointmentModal({ appointment, timeZone, onClose }: { appointment: Appointment; timeZone?: string; onClose: () => void }) {
  const queryClient = useQueryClient();
  const cancel = useMutation({
    mutationFn: () => api.delete(`/appointments/${appointment.id}`),
    onSuccess: () => {
      queryClient.invalidateQueries();
      onClose();
    },
  });
  const sourceLabel = { google: 'Google Calendar', ai: 'Booked by the AI', manual: 'Added manually' }[appointment.source];

  return (
    <Modal title={appointment.client_name} onClose={onClose}>
      <dl className="space-y-3 text-sm">
        <div className="flex justify-between gap-4"><dt className="text-gray-500">When</dt><dd className="font-medium text-gray-900">{formatDateTime(appointment.start_time, timeZone)}</dd></div>
        <div className="flex justify-between gap-4"><dt className="text-gray-500">Service</dt><dd className="font-medium text-gray-900">{appointment.service_type ?? '—'}</dd></div>
        <div className="flex justify-between gap-4"><dt className="text-gray-500">Source</dt><dd className="font-medium text-gray-900">{sourceLabel}</dd></div>
      </dl>
      {cancel.isError && <p className="mt-4 text-sm text-red-600">{errorMessage(cancel.error)}</p>}
      <div className="flex justify-end gap-2 mt-6">
        <button onClick={onClose} className={secondaryButton}>Close</button>
        <button
          onClick={() => window.confirm('Cancel this appointment? It will also be removed from Google Calendar.') && cancel.mutate()}
          disabled={cancel.isPending}
          className="flex items-center justify-center px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 transition-colors disabled:opacity-50"
        >
          {cancel.isPending ? 'Cancelling…' : 'Cancel Appointment'}
        </button>
      </div>
    </Modal>
  );
}
