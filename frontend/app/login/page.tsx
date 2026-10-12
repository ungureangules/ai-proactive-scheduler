'use client';

import { useState } from 'react';
import { api, errorMessage } from '../../src/lib/api';
import { setToken } from '../../src/lib/auth';
import { inputClass, labelClass, primaryButton } from '../../src/components/Modal';

export default function LoginPage() {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [businessName, setBusinessName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      const { data } =
        mode === 'login'
          ? await api.post('/auth/login', new URLSearchParams({ username: email, password }))
          : await api.post('/auth/register', {
              business_name: businessName,
              email,
              password,
              timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            });
      setToken(data.access_token);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-full flex items-center justify-center p-8">
      <div className="w-full max-w-sm">
        <h1 className="text-3xl font-bold text-gray-900 text-center mb-2">AI Scheduler</h1>
        <p className="text-gray-500 text-center mb-8">
          {mode === 'login' ? 'Sign in to your business dashboard.' : 'Create an account for your business.'}
        </p>
        <form onSubmit={submit} className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-4">
          {mode === 'register' && (
            <div>
              <label className={labelClass} htmlFor="business">Business Name</label>
              <input id="business" required value={businessName} onChange={(e) => setBusinessName(e.target.value)} className={inputClass} />
            </div>
          )}
          <div>
            <label className={labelClass} htmlFor="email">Email Address</label>
            <input id="email" type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} className={inputClass} />
          </div>
          <div>
            <label className={labelClass} htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              required
              minLength={mode === 'register' ? 8 : undefined}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={inputClass}
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button type="submit" disabled={submitting} className={`${primaryButton} w-full`}>
            {submitting ? 'Please wait…' : mode === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        </form>
        <p className="text-sm text-gray-500 text-center mt-4">
          {mode === 'login' ? 'New here?' : 'Already have an account?'}{' '}
          <button
            onClick={() => {
              setMode(mode === 'login' ? 'register' : 'login');
              setError('');
            }}
            className="text-blue-600 font-medium hover:underline"
          >
            {mode === 'login' ? 'Create an account' : 'Sign in'}
          </button>
        </p>
      </div>
    </div>
  );
}
