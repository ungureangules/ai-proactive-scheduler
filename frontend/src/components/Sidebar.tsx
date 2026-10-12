import Link from 'next/link';
import { LayoutDashboard, Calendar, Users, Settings, MessageSquare } from 'lucide-react';

export default function Sidebar() {
  return (
    <div className="w-64 bg-gray-900 h-screen text-white flex flex-col">
      <div className="p-6 text-2xl font-bold border-b border-gray-800">
        AI Scheduler
      </div>
      <nav className="flex-1 mt-6">
        <Link href="/" className="flex items-center px-6 py-3 text-gray-300 hover:bg-gray-800 hover:text-white transition-colors">
          <LayoutDashboard className="mr-3 w-5 h-5" />
          Dashboard
        </Link>
        <Link href="/calendar" className="flex items-center px-6 py-3 text-gray-300 hover:bg-gray-800 hover:text-white transition-colors">
          <Calendar className="mr-3 w-5 h-5" />
          Calendar
        </Link>
        <Link href="/clients" className="flex items-center px-6 py-3 text-gray-300 hover:bg-gray-800 hover:text-white transition-colors">
          <Users className="mr-3 w-5 h-5" />
          Clients
        </Link>
        <Link href="/conversations" className="flex items-center px-6 py-3 text-gray-300 hover:bg-gray-800 hover:text-white transition-colors">
          <MessageSquare className="mr-3 w-5 h-5" />
          Conversations
        </Link>
        <Link href="/settings" className="flex items-center px-6 py-3 text-gray-300 hover:bg-gray-800 hover:text-white transition-colors">
          <Settings className="mr-3 w-5 h-5" />
          Settings
        </Link>
      </nav>
      <div className="p-6 border-t border-gray-800">
        <div className="flex items-center">
          <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center font-bold text-sm mr-3">
            B
          </div>
          <span className="text-sm font-medium">Business Owner</span>
        </div>
      </div>
    </div>
  );
}
