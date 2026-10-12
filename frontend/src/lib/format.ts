export function formatDate(iso: string, timeZone?: string) {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone });
}

export function formatTime(iso: string, timeZone?: string) {
  return new Date(iso).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', timeZone });
}

export function formatDateTime(iso: string, timeZone?: string) {
  return `${formatDate(iso, timeZone)} at ${formatTime(iso, timeZone)}`;
}

/** "YYYY-MM-DD" of an instant as seen in `timeZone`. */
export function dateKey(date: Date, timeZone?: string) {
  return date.toLocaleDateString('en-CA', { timeZone });
}

export function relativeTime(iso: string, now: number) {
  const minutes = Math.round((now - new Date(iso).getTime()) / 60000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes} min${minutes === 1 ? '' : 's'} ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`;
  const days = Math.round(hours / 24);
  return `${days} day${days === 1 ? '' : 's'} ago`;
}

export function frequencyLabel(days: number | null) {
  if (!days) return 'Not enough visits yet';
  if (days % 7 === 0) return `Every ${days / 7} week${days === 7 ? '' : 's'}`;
  return `Every ${days} days`;
}

export function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join('');
}
