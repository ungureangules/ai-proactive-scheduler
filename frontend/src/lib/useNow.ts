import { useEffect, useState } from 'react';

/** Current time in ms, refreshed every `intervalMs` (keeps "x mins ago" and "today" current). */
export function useNow(intervalMs = 60_000) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return now;
}
