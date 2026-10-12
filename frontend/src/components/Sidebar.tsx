'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { LayoutDashboard, Calendar, Users, Settings, MessageSquare, LogOut } from 'lucide-react';
import { useBusiness } from '../lib/api';
import { setToken } from '../lib/auth';
import { initials } from '../lib/format';

const links = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/calendar', label: 'Calendar', icon: Calendar },
  { href: '/clients', label: 'Clients', icon: Users },
  { href: '/conversations', label: 'Conversations', icon: MessageSquare },
  { href: '/settings', label: 'Settings', icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();
  const queryClient = useQueryClient();
  const { data: business } = useBusiness();

  const logout = () => {
    setToken(null);
    queryClient.clear();
  };

  return (
    <div className="w-64 bg-gray-900 h-full text-white flex flex-col flex-shrink-0">
      <div className="p-6 text-2xl font-bold border-b border-gray-800">
        AI Scheduler
      </div>
      <nav className="flex-1 mt-6">
        {links.map(({ href, label, icon: Icon }) => {
          const active = href === '/' ? pathname === '/' : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? 'page' : undefined}
              className={`flex items-center px-6 py-3 transition-colors ${
                active ? 'bg-gray-800 text-white' : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              }`}
            >
              <Icon className="mr-3 w-5 h-5" />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="p-6 border-t border-gray-800">
        <div className="flex items-center">
          <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center font-bold text-sm mr-3 flex-shrink-0">
            {business ? initials(business.name) : ''}
          </div>
          <span className="text-sm font-medium truncate flex-1">{business?.name ?? ''}</span>
          <button onClick={logout} title="Log out" className="ml-2 p-1.5 rounded text-gray-400 hover:text-white hover:bg-gray-800">
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
