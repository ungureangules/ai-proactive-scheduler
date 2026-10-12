'use client';

import { Suspense, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Calendar, Clock, MessageCircle, Shield, User } from 'lucide-react';
import { api, errorMessage, useBusiness, useIntegrations } from '../../src/lib/api';
import { inputClass, labelClass } from '../../src/components/Modal';
import type { Business, WorkingHours } from '../../src/lib/types';

const DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];

export default function SettingsPage() {
  return (
    <div className="p-8 max-w-4xl">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-500">Manage your business profile and integrations.</p>
      </header>
      <Suspense fallback={null}>
        <GoogleResultBanner />
      </Suspense>
      <div className="space-y-6">
        <IntegrationsSection />
        <ProfileSection />
      </div>
    </div>
  );
}

function GoogleResultBanner() {
  const result = useSearchParams().get('google');
  if (result === 'connected') {
    return <p className="mb-6 text-sm text-green-700 bg-green-50 border border-green-100 rounded-lg px-4 py-3">Google Calendar connected. Your appointments will sync within the hour, or sync now from the Calendar page.</p>;
  }
  if (result === 'error') {
    return <p className="mb-6 text-sm text-red-700 bg-red-50 border border-red-100 rounded-lg px-4 py-3">Google Calendar could not be connected. Please try again.</p>;
  }
  return null;
}

function IntegrationsSection() {
  const queryClient = useQueryClient();
  const { data: integrations } = useIntegrations();
  const connect = useMutation({
    mutationFn: async () => (await api.get<{ url: string }>('/businesses/me/google/auth-url')).data,
    onSuccess: ({ url }) => {
      window.location.href = url;
    },
  });
  const disconnect = useMutation({
    mutationFn: () => api.delete('/businesses/me/google'),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['integrations'] }),
  });
  const google = integrations?.google;
  const twilio = integrations?.twilio;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <h2 className="text-xl font-bold text-gray-900 mb-6 flex items-center">
        <Shield className="mr-2 w-5 h-5 text-blue-600" />
        Integrations
      </h2>

      <div className="flex items-center justify-between gap-4 p-4 border border-gray-100 rounded-lg bg-gray-50">
        <div className="flex items-center min-w-0">
          <div className="bg-white p-2 rounded shadow-sm mr-4">
            <Calendar className="w-8 h-8 text-blue-600" />
          </div>
          <div className="min-w-0">
            <h3 className="font-bold text-gray-900">Google Calendar</h3>
            <p className="text-sm text-gray-500 truncate">
              {google?.connected ? `Connected as ${google.account_email ?? 'your Google account'}` : 'Sync your appointments and availability.'}
            </p>
          </div>
        </div>
        {google?.connected ? (
          <button
            onClick={() => window.confirm('Disconnect Google Calendar? The AI will stop booking into it.') && disconnect.mutate()}
            disabled={disconnect.isPending}
            className="border border-gray-200 bg-white text-gray-700 px-4 py-2 rounded-lg font-medium hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            Disconnect
          </button>
        ) : (
          <button
            onClick={() => connect.mutate()}
            disabled={connect.isPending || !integrations}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            {connect.isPending ? 'Redirecting…' : 'Connect'}
          </button>
        )}
      </div>
      {(connect.isError || disconnect.isError) && (
        <p className="mt-2 text-sm text-red-600">{errorMessage(connect.error ?? disconnect.error)}</p>
      )}

      <div className="mt-4 flex items-center justify-between gap-4 p-4 border border-gray-100 rounded-lg bg-gray-50">
        <div className="flex items-center">
          <div className="bg-white p-2 rounded shadow-sm mr-4">
            <MessageCircle className="w-8 h-8 text-green-600" />
          </div>
          <div>
            <h3 className="font-bold text-gray-900">Twilio (WhatsApp)</h3>
            <p className="text-sm text-gray-500">
              {twilio?.configured
                ? `Sending from ${twilio.whatsapp_number}.${twilio.outreach_template_configured ? '' : ' No outreach template set: proactive messages only reach clients who wrote in the last 24h.'}`
                : 'Not configured. Set the TWILIO_* variables on the server.'}
            </p>
          </div>
        </div>
        {twilio && (
          <span className={`text-sm font-medium flex items-center flex-shrink-0 ${twilio.configured ? 'text-green-600' : 'text-gray-500'}`}>
            <span className={`w-2 h-2 rounded-full mr-2 ${twilio.configured ? 'bg-green-600' : 'bg-gray-400'}`}></span>
            {twilio.configured ? 'Connected' : 'Not connected'}
          </span>
        )}
      </div>
    </div>
  );
}

function ProfileSection() {
  const { data: business } = useBusiness();
  if (!business) return null;
  return <ProfileForm key={business.id} business={business} />;
}

function ProfileForm({ business }: { business: Business }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState(business.name);
  const [email, setEmail] = useState(business.email);
  const [timezone, setTimezone] = useState(business.timezone);
  const [countryCode, setCountryCode] = useState(business.default_country_code ?? '');
  const [duration, setDuration] = useState(String(business.appointment_duration_minutes));
  const [outreach, setOutreach] = useState(business.outreach_enabled);
  const [hours, setHours] = useState<WorkingHours>(business.working_hours);
  const [saved, setSaved] = useState(false);

  const timezones = Intl.supportedValuesOf('timeZone');
  if (!timezones.includes(timezone)) timezones.unshift(timezone);

  const save = useMutation({
    mutationFn: () =>
      api.patch<Business>('/businesses/me', {
        name,
        email,
        timezone,
        default_country_code: countryCode || null,
        appointment_duration_minutes: Number(duration),
        outreach_enabled: outreach,
        working_hours: hours,
      }),
    onSuccess: ({ data }) => {
      queryClient.setQueryData(['business'], data);
      setSaved(true);
    },
  });

  const setDay = (day: string, value: { start: string; end: string } | null) => {
    setSaved(false);
    setHours({ ...hours, [day]: value });
  };

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        save.mutate();
      }}
      onChange={() => setSaved(false)}
      className="space-y-6"
    >
      {/* Business Profile */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-6 flex items-center">
          <User className="mr-2 w-5 h-5 text-blue-600" />
          Business Profile
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className={labelClass} htmlFor="name">Business Name</label>
            <input id="name" required value={name} onChange={(e) => setName(e.target.value)} className={inputClass} />
          </div>
          <div>
            <label className={labelClass} htmlFor="email">Email Address</label>
            <input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className={inputClass} />
          </div>
          <div>
            <label className={labelClass} htmlFor="timezone">Timezone</label>
            <select id="timezone" value={timezone} onChange={(e) => setTimezone(e.target.value)} className={inputClass}>
              {timezones.map((tz) => (
                <option key={tz} value={tz}>{tz.replaceAll('_', ' ')}</option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelClass} htmlFor="country">Default Country Code</label>
            <input
              id="country"
              inputMode="numeric"
              pattern="\d{1,4}"
              placeholder="e.g. 55 for Brazil"
              value={countryCode}
              onChange={(e) => setCountryCode(e.target.value.replace(/\D/g, ''))}
              className={inputClass}
            />
            <p className="text-xs text-gray-400 mt-1">Used for phone numbers written without a leading +.</p>
          </div>
        </div>
      </div>

      {/* Scheduling */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-6 flex items-center">
          <Clock className="mr-2 w-5 h-5 text-blue-600" />
          Scheduling
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          <div>
            <label className={labelClass} htmlFor="duration">Appointment Length (minutes)</label>
            <input id="duration" type="number" min={5} max={480} step={5} required value={duration} onChange={(e) => setDuration(e.target.value)} className={inputClass} />
          </div>
          <label className="flex items-center gap-3 md:mt-6 text-sm font-medium text-gray-700">
            <input type="checkbox" checked={outreach} onChange={(e) => setOutreach(e.target.checked)} className="w-4 h-4 accent-blue-600" />
            Let the AI contact clients when they&apos;re due
          </label>
        </div>

        <h3 className="text-sm font-semibold text-gray-700 mb-3">Opening Hours</h3>
        <div className="space-y-2">
          {DAYS.map((day) => {
            const value = hours[day];
            return (
              <div key={day} className="flex flex-wrap items-center gap-3 text-sm">
                <label className="flex items-center gap-2 w-32 font-medium text-gray-700 capitalize">
                  <input
                    type="checkbox"
                    checked={Boolean(value)}
                    onChange={(e) => setDay(day, e.target.checked ? { start: '09:00', end: '18:00' } : null)}
                    className="w-4 h-4 accent-blue-600"
                  />
                  {day}
                </label>
                {value ? (
                  <>
                    <input type="time" aria-label={`${day} opens`} value={value.start} onChange={(e) => setDay(day, { ...value, start: e.target.value })} className="p-1.5 border border-gray-200 rounded-lg" />
                    <span className="text-gray-400">to</span>
                    <input type="time" aria-label={`${day} closes`} value={value.end} onChange={(e) => setDay(day, { ...value, end: e.target.value })} className="p-1.5 border border-gray-200 rounded-lg" />
                  </>
                ) : (
                  <span className="text-gray-400">Closed</span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button type="submit" disabled={save.isPending} className="bg-gray-900 text-white px-6 py-2 rounded-lg font-medium hover:bg-black transition-colors disabled:opacity-50">
          {save.isPending ? 'Saving…' : 'Save Changes'}
        </button>
        {saved && <span className="text-sm text-green-600">Saved.</span>}
        {save.isError && <span className="text-sm text-red-600">{errorMessage(save.error)}</span>}
      </div>
    </form>
  );
}
