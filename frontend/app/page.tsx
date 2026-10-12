import { TrendingUp, Users, CalendarCheck, DollarSign } from 'lucide-react';

export default function Dashboard() {
  const metrics = [
    { title: "Total Appointments", value: "128", icon: CalendarCheck, color: "text-blue-600", bg: "bg-blue-100" },
    { title: "Rescued Revenue", value: "$3,450", icon: DollarSign, color: "text-green-600", bg: "bg-green-100" },
    { title: "New Clients", value: "12", icon: Users, color: "text-purple-600", bg: "bg-purple-100" },
    { title: "Conversion Rate", value: "24%", icon: TrendingUp, color: "text-orange-600", bg: "bg-orange-100" },
  ];

  const appointments = [
    { id: 1, client: "John Doe", service: "Haircut", date: "Oct 24, 2023", time: "2:00 PM", status: "AI Booked" },
    { id: 2, client: "Jane Smith", service: "Nail Polish", date: "Oct 24, 2023", time: "4:30 PM", status: "AI Booked" },
    { id: 3, client: "Robert Brown", service: "Beard Trim", date: "Oct 25, 2023", time: "10:00 AM", status: "Pending" },
    { id: 4, client: "Emily White", service: "Facial", date: "Oct 25, 2023", time: "11:30 AM", status: "AI Booked" },
  ];

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500">Welcome back! Here's what's happening with your AI assistant.</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
        {metrics.map((metric, i) => (
          <div key={i} className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
            <div className="flex items-center justify-between mb-4">
              <div className={`${metric.bg} p-3 rounded-lg`}>
                <metric.icon className={`w-6 h-6 ${metric.color}`} />
              </div>
            </div>
            <h3 className="text-gray-500 text-sm font-medium">{metric.title}</h3>
            <p className="text-2xl font-bold text-gray-900">{metric.value}</p>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="font-bold text-gray-900 text-lg">Upcoming Appointments</h2>
          <button className="text-blue-600 text-sm font-medium hover:underline">View All</button>
        </div>
        <table className="w-full text-left">
          <thead>
            <tr className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
              <th className="px-6 py-3 font-semibold">Client</th>
              <th className="px-6 py-3 font-semibold">Service</th>
              <th className="px-6 py-3 font-semibold">Date & Time</th>
              <th className="px-6 py-3 font-semibold">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 text-sm">
            {appointments.map((app) => (
              <tr key={app.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4 font-medium text-gray-900">{app.client}</td>
                <td className="px-6 py-4 text-gray-600">{app.service}</td>
                <td className="px-6 py-4 text-gray-600">{app.date} at {app.time}</td>
                <td className="px-6 py-4">
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    app.status === 'AI Booked' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                  }`}>
                    {app.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
