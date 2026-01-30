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
    { 
      id: 'all', 
      label: 'All Emails', 
      count: emailCounts.all, 
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
      )
    },
    { 
      id: 'unread', 
      label: 'Unread', 
      count: emailCounts.unread, 
      icon: (
        <div className="w-5 h-5 flex items-center justify-center">
          <div className="w-2.5 h-2.5 bg-primary-600 rounded-full"></div>
        </div>
      ),
      highlight: emailCounts.unread > 0
    },
    { 
      id: 'urgent', 
      label: 'Urgent', 
      count: emailCounts.urgent, 
      icon: (
        <svg className="w-5 h-5 text-urgent" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
        </svg>
      ),
      textColor: 'text-urgent',
      highlight: emailCounts.urgent > 0
    },
    { 
      id: 'normal', 
      label: 'Normal', 
      count: emailCounts.normal, 
      icon: (
        <svg className="w-5 h-5 text-normal" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      ),
      textColor: 'text-normal'
    },
    { 
      id: 'low', 
      label: 'Low Priority', 
      count: emailCounts.low, 
      icon: (
        <svg className="w-5 h-5 text-low" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
        </svg>
      ),
      textColor: 'text-low'
    },
  ];

  const accounts = [
    { name: 'Gmail', count: 1, status: 'connected' },
    { name: 'Outlook', count: 3, status: 'connected' },
    { name: 'Instantly', count: 1, status: 'connected' },
  ];

  return (
    <div className="w-64 bg-white border-r border-gray-200 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <h1 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <svg className="w-6 h-6 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
          Email Hub
        </h1>
        <p className="text-xs text-gray-500 mt-0.5">8 inboxes unified</p>
      </div>

      {/* Folders / Filters */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-2">
          <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide px-3 py-2">
            Folders
          </div>
          <nav className="space-y-0.5">
            {menuItems.map((item) => (
              <button
                key={item.id}
                onClick={() => setFilter(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-md text-sm font-medium transition-all duration-150 ${
                  filter === item.id
                    ? 'bg-primary-100 text-primary-900'
                    : item.highlight
                    ? 'text-gray-900 hover:bg-gray-100'
                    : 'text-gray-700 hover:bg-gray-50'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className={filter === item.id ? 'text-primary-600' : ''}>
                    {item.icon}
                  </div>
                  <span className={item.textColor || ''}>{item.label}</span>
                </div>
                {item.count > 0 && (
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                    filter === item.id
                      ? 'bg-primary-200 text-primary-900'
                      : 'bg-gray-200 text-gray-700'
                  }`}>
                    {item.count}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>

        {/* Accounts Section */}
        <div className="p-2 mt-4">
          <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide px-3 py-2">
            Accounts
          </div>
          <div className="space-y-1">
            {accounts.map((account, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between px-3 py-2 text-sm text-gray-700"
              >
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${
                    account.status === 'connected' ? 'bg-success' : 'bg-gray-300'
                  }`}></div>
                  <span className="font-medium">{account.name}</span>
                  {account.count > 1 && (
                    <span className="text-xs text-gray-500">({account.count})</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200 bg-gray-50">
        <div className="text-xs text-gray-600">
          <div className="flex items-center justify-between mb-1">
            <span>Last sync:</span>
            <span className="font-medium text-gray-900">Just now</span>
          </div>
          <div className="flex items-center justify-between">
            <span>Total emails:</span>
            <span className="font-medium text-gray-900">{emailCounts.all}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
