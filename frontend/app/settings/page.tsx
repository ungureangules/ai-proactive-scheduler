import { Calendar, Shield, Bell, User } from 'lucide-react';

export default function SettingsPage() {
  return (
    <div className="p-8 max-w-4xl">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-500">Manage your business profile and integrations.</p>
      </header>

      <div className="space-y-6">
        {/* Integrations Section */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-6 flex items-center">
            <Shield className="mr-2 w-5 h-5 text-blue-600" />
            Integrations
          </h2>
          
          <div className="flex items-center justify-between p-4 border border-gray-100 rounded-lg bg-gray-50">
            <div className="flex items-center">
              <div className="bg-white p-2 rounded shadow-sm mr-4">
                <img src="https://www.google.com/images/branding/googleg/1x/googleg_standard_color_128dp.png" alt="Google" className="w-8 h-8" />
              </div>
              <div>
                <h3 className="font-bold text-gray-900">Google Calendar</h3>
                <p className="text-sm text-gray-500">Sync your appointments and availability.</p>
              </div>
            </div>
            <button className="bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700 transition-colors">
              Connect
            </button>
          </div>

          <div className="mt-4 flex items-center justify-between p-4 border border-gray-100 rounded-lg bg-gray-50">
            <div className="flex items-center">
              <div className="bg-white p-2 rounded shadow-sm mr-4 flex items-center justify-center">
                <span className="text-red-600 font-bold text-xl">T</span>
              </div>
              <div>
                <h3 className="font-bold text-gray-900">Twilio (WhatsApp)</h3>
                <p className="text-sm text-gray-500">Enabled for client communications.</p>
              </div>
            </div>
            <span className="text-green-600 text-sm font-medium flex items-center">
              <span className="w-2 h-2 bg-green-600 rounded-full mr-2"></span>
              Connected
            </span>
          </div>
        </div>

        {/* Business Profile */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-6 flex items-center">
            <User className="mr-2 w-5 h-5 text-blue-600" />
            Business Profile
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Business Name</label>
              <input type="text" defaultValue="Gentleman's Barbershop" className="w-full p-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email Address</label>
              <input type="email" defaultValue="owner@barbershop.com" className="w-full p-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Timezone</label>
              <select className="w-full p-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                <option>UTC -5 (Eastern Time)</option>
                <option>UTC -8 (Pacific Time)</option>
                <option>UTC +0 (London)</option>
              </select>
            </div>
          </div>
          <button className="mt-6 bg-gray-900 text-white px-6 py-2 rounded-lg font-medium hover:bg-black transition-colors">
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
}
