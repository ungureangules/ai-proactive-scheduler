'use client';

import React, { useDeferredValue, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Search, Plus, Sparkles, Filter, Mail, Phone, Calendar, Pause, Play, Trash2 } from 'lucide-react';
import { api, errorMessage, useBusiness } from '../../src/lib/api';
import { formatDate, frequencyLabel } from '../../src/lib/format';
import Modal, { inputClass, labelClass, primaryButton, secondaryButton } from '../../src/components/Modal';
import StatusBadge from '../../src/components/StatusBadge';
import type { Client, ClientStatus } from '../../src/lib/types';

const statusOptions: { value: '' | ClientStatus; label: string }[] = [
  { value: '', label: 'All statuses' },
  { value: 'due', label: 'Due for outreach' },
  { value: 'negotiating', label: 'AI negotiating' },
  { value: 'booked', label: 'Booked' },
  { value: 'paused', label: 'Paused / manual' },
  { value: 'idle', label: 'Idle' },
  { value: 'opted_out', label: 'Opted out' },
];

function confidenceLabel(confidence: number | null) {
  if (confidence === null) return null;
  const level = confidence >= 0.8 ? 'High' : confidence >= 0.5 ? 'Medium' : 'Low';
  return `${level} (${Math.round(confidence * 100)}%)`;
}

export default function ClientsPage() {
  const queryClient = useQueryClient();
  const { data: business } = useBusiness();
  const tz = business?.timezone;
  const [searchTerm, setSearchTerm] = useState('');
  const [status, setStatus] = useState<'' | ClientStatus>('');
  const [adding, setAdding] = useState(false);
  const search = useDeferredValue(searchTerm.trim());

  const { data: clients = [], isLoading, isError } = useQuery({
    queryKey: ['clients', search, status],
    queryFn: async () =>
      (await api.get<Client[]>('/clients/', { params: { search: search || undefined, status: status || undefined } })).data,
    placeholderData: (previous) => previous,
  });

  const update = useMutation({
    mutationFn: ({ id, changes }: { id: number; changes: Partial<Client> }) => api.patch(`/clients/${id}`, changes),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['clients'] }),
  });
  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`/clients/${id}`),
    onSuccess: () => queryClient.invalidateQueries(),
  });

  return (
    <div className="p-8">
      <header className="mb-8 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Clients</h1>
          <p className="text-gray-500">View and manage clients and AI frequency analysis.</p>
        </div>
        <button onClick={() => setAdding(true)} className={`${primaryButton} self-start md:self-auto`}>
          <Plus className="w-4 h-4 mr-2" />
          Add Client
        </button>
      </header>

      {/* Toolbar */}
      <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-100 flex flex-col md:flex-row gap-4 justify-between items-center mb-6">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by name, email or phone..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
        <div className="relative w-full md:w-56">
          <Filter className="w-4 h-4 text-gray-500 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <select
            aria-label="Filter by status"
            value={status}
            onChange={(e) => setStatus(e.target.value as '' | ClientStatus)}
            className="w-full pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm font-medium text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {statusOptions.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </div>
      </div>

      {(update.isError || remove.isError) && (
        <p className="mb-4 text-sm text-red-600">{errorMessage(update.error ?? remove.error)}</p>
      )}

      {/* Clients Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider border-b border-gray-100">
                <th className="px-6 py-4 font-semibold">Client Details</th>
                <th className="px-6 py-4 font-semibold">Last Service</th>
                <th className="px-6 py-4 font-semibold">AI Suggested Frequency</th>
                <th className="px-6 py-4 font-semibold">Next Outreach</th>
                <th className="px-6 py-4 font-semibold">AI Status</th>
                <th className="px-6 py-4 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 text-sm">
              {clients.map((client) => (
                <tr key={client.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4">
                    <div>
                      <div className="font-semibold text-gray-900">{client.name}</div>
                      {client.email && (
                        <div className="text-gray-500 text-xs flex items-center mt-1">
                          <Mail className="w-3.5 h-3.5 mr-1" />
                          {client.email}
                        </div>
                      )}
                      <div className="text-gray-500 text-xs flex items-center mt-0.5">
                        <Phone className="w-3.5 h-3.5 mr-1" />
                        {client.phone_number ?? 'No phone number'}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div>
                      <div className="text-gray-900 font-medium">{client.last_service_type ?? '—'}</div>
                      {client.last_visit && (
                        <div className="text-gray-500 text-xs flex items-center mt-1">
                          <Calendar className="w-3.5 h-3.5 mr-1" />
                          {formatDate(client.last_visit, tz)}
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-1.5">
                      <Sparkles className="w-4 h-4 text-purple-600 flex-shrink-0" />
                      <div>
                        <div className="text-gray-900 font-medium">{frequencyLabel(client.avg_frequency_days)}</div>
                        {client.frequency_confidence !== null && (
                          <div className="text-gray-400 text-[11px]">Confidence: {confidenceLabel(client.frequency_confidence)}</div>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 font-medium text-gray-700">
                    {client.next_appointment
                      ? <span className="text-green-700">Booked {formatDate(client.next_appointment, tz)}</span>
                      : client.next_outreach ? formatDate(client.next_outreach, tz) : '—'}
                  </td>
                  <td className="px-6 py-4">
                    <StatusBadge status={client.status} />
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex justify-end gap-1">
                      <button
                        onClick={() => update.mutate({ id: client.id, changes: { ai_paused: !client.ai_paused } })}
                        title={client.ai_paused ? 'Resume AI for this client' : 'Pause AI for this client'}
                        className="p-1.5 hover:bg-gray-100 rounded text-gray-400 hover:text-gray-600"
                      >
                        {client.ai_paused ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
                      </button>
                      <button
                        onClick={() => window.confirm(`Delete ${client.name} and their history?`) && remove.mutate(client.id)}
                        title="Delete client"
                        className="p-1.5 hover:bg-red-50 rounded text-gray-400 hover:text-red-600"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!isLoading && clients.length === 0 && (
            <p className="px-6 py-10 text-center text-sm text-gray-500">
              {isError ? 'Could not load clients.' : search || status ? 'No clients match your filters.' : 'No clients yet. Add one, or sync Google Calendar to import them.'}
            </p>
          )}
        </div>
      </div>

      {adding && <AddClientModal onClose={() => setAdding(false)} />}
    </div>
  );
}

function AddClientModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({ name: '', phone_number: '', email: '', notes: '' });
  const create = useMutation({
    mutationFn: () => api.post('/clients/', { ...form, email: form.email || null, notes: form.notes || null }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] });
      onClose();
    },
  });
  const field = (key: keyof typeof form) => ({
    value: form[key],
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setForm({ ...form, [key]: e.target.value }),
  });

  return (
    <Modal title="Add Client" onClose={onClose}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          create.mutate();
        }}
        className="space-y-4"
      >
        <div>
          <label className={labelClass} htmlFor="name">Name</label>
          <input id="name" required {...field('name')} className={inputClass} />
        </div>
        <div>
          <label className={labelClass} htmlFor="phone">WhatsApp Number</label>
          <input id="phone" required placeholder="+55 11 99999-9999" {...field('phone_number')} className={inputClass} />
        </div>
        <div>
          <label className={labelClass} htmlFor="email">Email (optional)</label>
          <input id="email" type="email" {...field('email')} className={inputClass} />
        </div>
        <div>
          <label className={labelClass} htmlFor="notes">Notes (optional)</label>
          <textarea id="notes" rows={2} {...field('notes')} className={inputClass} />
        </div>
        <p className="text-xs text-gray-400">
          Past visits are linked automatically when Google Calendar events use this client&apos;s name or phone number.
        </p>
        {create.isError && <p className="text-sm text-red-600">{errorMessage(create.error)}</p>}
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className={secondaryButton}>Cancel</button>
          <button type="submit" disabled={create.isPending} className={primaryButton}>
            {create.isPending ? 'Saving…' : 'Add Client'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
