'use client';

import { useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { useToken } from '../lib/auth';
import Sidebar from './Sidebar';

const PUBLIC_PATHS = ['/login'];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const token = useToken();
  const pathname = usePathname();
  const router = useRouter();
  const isPublic = PUBLIC_PATHS.includes(pathname);

  useEffect(() => {
    if (token === null && !isPublic) router.replace('/login');
    if (token && isPublic) router.replace('/');
  }, [token, isPublic, router]);

  if (isPublic) return <main className="flex-1 h-full overflow-y-auto">{children}</main>;
  if (!token) return <div className="flex-1 grid place-items-center text-sm text-gray-400">Loading…</div>;

  return (
    <>
      <Sidebar />
      <main className="flex-1 h-full overflow-y-auto">{children}</main>
    </>
  );
}
