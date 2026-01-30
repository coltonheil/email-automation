interface EmailListProps {
  emails: any[];
  selectedEmail: any;
  onSelectEmail: (email: any) => void;
  loading: boolean;
}

export default function EmailList({ emails, selectedEmail, onSelectEmail, loading }: EmailListProps) {
  if (loading) {
    return (
      <div className="p-4 space-y-2">
        {[...Array(10)].map((_, i) => (
          <div key={i} className="animate-pulse">
            <div className="h-20 bg-gray-100 rounded-lg"></div>
          </div>
        ))}
      </div>
    );
  }

  if (emails.length === 0) {
    return (
      <div className="p-8 text-center text-gray-500">
        <svg className="mx-auto h-12 w-12 text-gray-300 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
        </svg>
        <p className="text-sm">No emails found</p>
      </div>
    );
  }

  const getPriorityColor = (category: string) => {
    if (category === 'urgent') return 'border-l-red-500';
    if (category === 'normal') return 'border-l-blue-500';
    return 'border-l-gray-300';
  };

  const getPriorityBadge = (category: string, score: number) => {
    if (category === 'urgent') {
      return <span className="text-xs px-2 py-0.5 bg-red-100 text-red-700 rounded-full font-medium">{score}</span>;
    }
    if (category === 'normal') {
      return <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full font-medium">{score}</span>;
    }
    return <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full font-medium">{score}</span>;
  };

  return (
    <div className="divide-y divide-gray-100">
      {emails.map((email) => (
        <button
          key={email.id}
          onClick={() => onSelectEmail(email)}
          className={`w-full text-left p-4 hover:bg-gray-50 transition-colors border-l-4 ${getPriorityColor(email.priority_category)} ${
            selectedEmail?.id === email.id ? 'bg-blue-50' : ''
          }`}
        >
          <div className="flex items-start justify-between gap-2 mb-1">
            <div className="flex items-center gap-2 flex-1 min-w-0">
              {email.is_unread && (
                <span className="w-2 h-2 bg-blue-600 rounded-full flex-shrink-0"></span>
              )}
              <span className={`text-sm truncate ${email.is_unread ? 'font-semibold text-gray-900' : 'font-medium text-gray-700'}`}>
                {email.from.split('<')[0].trim() || email.from}
              </span>
            </div>
            {getPriorityBadge(email.priority_category, email.priority_score)}
          </div>
          
          <h3 className={`text-sm mb-1 truncate ${email.is_unread ? 'font-semibold text-gray-900' : 'text-gray-700'}`}>
            {email.subject}
          </h3>
          
          <p className="text-xs text-gray-500 truncate mb-2">
            {email.snippet}
          </p>

          <div className="flex items-center justify-between text-xs text-gray-400">
            <span className="uppercase font-medium">{email.provider}</span>
            <span>{new Date(email.received_at).toLocaleDateString()}</span>
          </div>
        </button>
      ))}
    </div>
  );
}
