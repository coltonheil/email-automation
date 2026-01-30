interface SidebarProps {
  filter: string;
  setFilter: (filter: string) => void;
  emailCounts: {
    all: number;
    unread: number;
    urgent: number;
    normal: number;
    low: number;
  };
}

export default function Sidebar({ filter, setFilter, emailCounts }: SidebarProps) {
  const menuItems = [
    { id: 'all', label: 'All Emails', count: emailCounts.all, icon: '📬' },
    { id: 'unread', label: 'Unread', count: emailCounts.unread, icon: '●' },
    { id: 'urgent', label: 'Urgent', count: emailCounts.urgent, icon: '🚨', color: 'text-red-600' },
    { id: 'normal', label: 'Normal', count: emailCounts.normal, icon: '📋', color: 'text-blue-600' },
    { id: 'low', label: 'Low Priority', count: emailCounts.low, icon: '📉', color: 'text-gray-500' },
  ];

  return (
    <div className="w-64 bg-gray-900 text-white p-4 flex flex-col">
      <div className="mb-8">
        <h1 className="text-xl font-bold">📧 Email Hub</h1>
        <p className="text-xs text-gray-400 mt-1">8 inboxes unified</p>
      </div>

      <nav className="space-y-1 flex-1">
        {menuItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setFilter(item.id)}
            className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors ${
              filter === item.id
                ? 'bg-gray-800 text-white'
                : 'text-gray-300 hover:bg-gray-800 hover:text-white'
            }`}
          >
            <div className="flex items-center gap-2">
              <span>{item.icon}</span>
              <span className={item.color || ''}>{item.label}</span>
            </div>
            {item.count > 0 && (
              <span className="bg-gray-700 text-xs px-2 py-0.5 rounded-full">
                {item.count}
              </span>
            )}
          </button>
        ))}
      </nav>

      <div className="mt-auto pt-4 border-t border-gray-800 text-xs text-gray-400">
        <div className="space-y-1">
          <div className="flex justify-between">
            <span>Gmail</span>
            <span className="text-green-400">●</span>
          </div>
          <div className="flex justify-between">
            <span>Outlook (3)</span>
            <span className="text-green-400">●</span>
          </div>
          <div className="flex justify-between">
            <span>Instantly</span>
            <span className="text-green-400">●</span>
          </div>
        </div>
      </div>
    </div>
  );
}
