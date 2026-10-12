import axios, { AxiosError } from 'axios';
import { useQuery } from '@tanstack/react-query';
import { getToken, setToken } from './auth';
import type { Business, Integrations } from './types';

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1',
});

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // An expired session logs out; a failed login attempt is just shown on the form
    if (error.response?.status === 401 && !error.config?.url?.startsWith('/auth/login')) {
      setToken(null);
    }
    return Promise.reject(error);
  },
);

export function errorMessage(error: unknown, fallback = 'Something went wrong'): string {
  if (error instanceof AxiosError) {
    const detail = (error.response?.data as { detail?: unknown } | undefined)?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg).replace(/^Value error, /, '');
    if (!error.response) return 'Cannot reach the server';
  }
  return fallback;
}

export function useBusiness() {
  return useQuery({ queryKey: ['business'], queryFn: async () => (await api.get<Business>('/auth/me')).data });
}

export function useIntegrations() {
  return useQuery({
    queryKey: ['integrations'],
    queryFn: async () => (await api.get<Integrations>('/businesses/me/integrations')).data,
  });
}
