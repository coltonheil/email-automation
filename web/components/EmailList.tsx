interface EmailListProps {
  emails: any[];
  selectedEmail: any;
  onSelectEmail: (email: any) => void;
  loading: boolean;
}

export default function EmailList({ emails, selectedEmail, onSelectEmail, loading }: EmailListProps) {
  if (loading) {
    return (
      <div className="p-2 space-y-1">
        {[...Array(10)].map((_, i) => (
          <div key={i} className="animate-pulse bg-white p-4 rounded-md border border-gray-200">
            <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
            <div className="h-3 bg-gray-100 rounded w-1/2 mb-2"></div>
            <div className="h-3 bg-gray-100 rounded w-full"></div>
          </div>
        ))}
      </div>
    );
  }

  if (emails.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center">
        <svg 
          className="w-16 h-16 text-gray-300 mb-4" 
          fill="none" 
          viewBox="0 0 24 24" 
          stroke="currentColor"
        >
          <path 
            strokeLinecap="round" 
            strokeLinejoin="round" 
            strokeWidth={1.5} 
            d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" 
          />
        </svg>
        <p className="text-sm font-medium text-gray-900 mb-1">No emails found</p>
        <p className="text-xs text-gray-500">Try changing your filter or syncing again</p>
      </div>
    );
  }

  const getPriorityBadge = (category: string, score: number) => {
    const baseClasses = "badge";
    if (category === 'urgent') {
      return <span className={`${baseClasses} badge-urgent`}>{score}</span>;
    }
    if (category === 'normal') {
      return <span className={`${baseClasses} badge-normal`}>{score}</span>;
    }
    return <span className={`${baseClasses} badge-low`}>{score}</span>;
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const getProviderIcon = (provider: string) => {
    const baseClasses = "text-xs font-semibold uppercase tracking-wide";
    const colors = {
      gmail: 'text-red-600',
      outlook: 'text-blue-600',
      instantly: 'text-purple-600',
    };
    return (
      <span className={`${baseClasses} ${colors[provider.toLowerCase() as keyof typeof colors] || 'text-gray-600'}`}>
        {provider}
      </span>
    );
  };

  return (
    <div className="h-full overflow-y-auto bg-gray-50">
      <div className="p-2 space-y-1">
        {emails.map((email) => {
          const isSelected = selectedEmail?.id === email.id;
          const isUnread = email.is_unread;
          
          return (
            <button
              key={email.id}
              onClick={() => onSelectEmail(email)}
              className={`w-full text-left transition-all duration-150 rounded-md border ${
                isSelected
                  ? 'email-item-selected shadow-sm'
                  : 'email-item bg-white border-gray-200 hover:shadow-sm'
              }`}
            >
              <div className="p-3">
                {/* Header: Priority badge + Subject */}
                <div className="flex items-start gap-2 mb-1.5">
                  {isUnread && <div className="unread-dot mt-1.5 flex-shrink-0"></div>}
                  <div className="flex-1 min-w-0">
                    <h3 className={`text-sm leading-snug truncate ${
                      isUnread ? 'font-semibold text-gray-900' : 'font-medium text-gray-700'
                    }`}>
                      {email.subject || '(No Subject)'}
                    </h3>
                  </div>
                  {getPriorityBadge(email.priority_category, email.priority_score)}
                </div>

                {/* Sender */}
                <div className={`text-sm mb-1 truncate ${
                  isUnread ? 'font-medium text-gray-900' : 'text-gray-700'
                }`}>
                  {email.from.split('<')[0].trim() || email.from}
                </div>

                {/* Snippet */}
                <p className="text-xs text-gray-500 line-clamp-2 leading-relaxed mb-2">
                  {email.snippet || email.body?.substring(0, 120) || 'No preview available'}
                </p>

                {/* Footer: Provider + Time + Attachments */}
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    {getProviderIcon(email.provider)}
                    <span className="text-gray-400">•</span>
                    <span className="text-gray-500">{formatTime(email.received_at)}</span>
                  </div>
                  {email.has_attachments && (
                    <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                    </svg>
                  )}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
