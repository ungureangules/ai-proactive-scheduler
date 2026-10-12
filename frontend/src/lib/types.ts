export type WorkingHours = Record<string, { start: string; end: string } | null>;

export interface Business {
  id: number;
  name: string;
  email: string;
  timezone: string;
  working_hours: WorkingHours;
  appointment_duration_minutes: number;
  default_country_code: string | null;
  outreach_enabled: boolean;
}

export interface Integrations {
  google: { connected: boolean; account_email: string | null; calendar_id: string | null; last_synced_at: string | null };
  twilio: { configured: boolean; whatsapp_number: string | null; outreach_template_configured: boolean };
}

export type ClientStatus = 'idle' | 'due' | 'negotiating' | 'booked' | 'paused' | 'opted_out';

export interface Client {
  id: number;
  name: string;
  phone_number: string | null;
  email: string | null;
  notes: string | null;
  avg_frequency_days: number | null;
  frequency_confidence: number | null;
  last_service_type: string | null;
  last_visit: string | null;
  next_appointment: string | null;
  next_outreach: string | null;
  status: ClientStatus;
  ai_paused: boolean;
  opted_out: boolean;
}

export interface Appointment {
  id: number;
  client_id: number;
  client_name: string;
  start_time: string;
  end_time: string;
  service_type: string | null;
  status: string;
  source: 'google' | 'ai' | 'manual';
}

export interface Conversation {
  client_id: number;
  client_name: string;
  phone_number: string | null;
  last_message: string;
  last_message_at: string;
  unread: boolean;
  status: ClientStatus;
  ai_paused: boolean;
}

export interface Message {
  id: number;
  message_body: string;
  direction: 'inbound' | 'outbound';
  sender: 'client' | 'ai' | 'staff' | 'system';
  status: 'received' | 'sent' | 'failed';
  error: string | null;
  timestamp: string;
}

export interface Dashboard {
  upcoming_appointments: number;
  ai_bookings_30d: number;
  outreach_sent_30d: number;
  conversion_rate_30d: number | null;
  active_clients: number;
  upcoming: Appointment[];
}
