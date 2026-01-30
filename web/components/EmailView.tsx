interface EmailViewProps {
  email: any;
}

export default function EmailView({ email }: EmailViewProps) {
  const getPriorityBadge = (category: string, score: number) => {
    if (category === 'urgent') {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-urgent-bg text-urgent-text rounded-full text-xs font-semibold">
          <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          Urgent • {score}
        </span>
      );
    }
    if (category === 'normal') {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-normal-bg text-normal-text rounded-full text-xs font-semibold">
          Normal • {score}
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-low-bg text-low-text rounded-full text-xs font-semibold">
        Low Priority • {score}
      </span>
    );
  };

  const formatDateTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header Section */}
      <div className="border-b border-gray-200 bg-white">
        <div className="p-6">
          {/* Subject and Priority */}
          <div className="mb-4">
            <div className="flex items-start justify-between gap-4 mb-2">
              <h1 className="text-2xl font-semibold text-gray-900 leading-tight flex-1">
                {email.subject || '(No Subject)'}
              </h1>
              {getPriorityBadge(email.priority_category, email.priority_score)}
            </div>
            
            {/* Status badges */}
            <div className="flex items-center gap-2 flex-wrap">
              {email.is_unread && (
                <span className="inline-flex items-center gap-1.5 px-2 py-1 bg-primary-100 text-primary-800 rounded text-xs font-medium">
                  <div className="w-1.5 h-1.5 bg-primary-600 rounded-full"></div>
                  Unread
                </span>
              )}
              {email.has_attachments && (
                <span className="inline-flex items-center gap-1.5 px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs font-medium">
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                  </svg>
                  Attachments
                </span>
              )}
              <span className="inline-flex items-center px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs font-semibold uppercase tracking-wide">
                {email.provider}
              </span>
            </div>
          </div>

          {/* Email metadata */}
          <div className="space-y-2 text-sm mb-4">
            <div className="flex items-start">
              <span className="w-16 text-gray-500 font-medium flex-shrink-0">From:</span>
              <span className="text-gray-900">{email.from}</span>
            </div>
            <div className="flex items-start">
              <span className="w-16 text-gray-500 font-medium flex-shrink-0">To:</span>
              <span className="text-gray-900">{email.to}</span>
            </div>
            {email.cc && (
              <div className="flex items-start">
                <span className="w-16 text-gray-500 font-medium flex-shrink-0">CC:</span>
                <span className="text-gray-700">{email.cc}</span>
              </div>
            )}
            <div className="flex items-start">
              <span className="w-16 text-gray-500 font-medium flex-shrink-0">Date:</span>
              <span className="text-gray-700">{formatDateTime(email.received_at)}</span>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex flex-wrap gap-2 pt-4 border-t border-gray-200">
            <button className="btn btn-primary flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
              </svg>
              Reply
            </button>
            <button className="btn btn-secondary flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
              Forward
            </button>
            <button className="btn btn-secondary flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
              </svg>
              Archive
            </button>
            {email.is_unread && (
              <button className="btn btn-secondary flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Mark Read
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Email Body */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-3xl">
          {email.body ? (
            <div className="prose prose-sm max-w-none">
              <pre className="whitespace-pre-wrap font-sans text-sm text-gray-800 leading-relaxed">
                {email.body}
              </pre>
            </div>
          ) : email.snippet ? (
            <div className="text-sm text-gray-700 leading-relaxed">
              <p className="mb-4">{email.snippet}</p>
              <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg text-xs text-gray-500">
                <p className="flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Full email body not available. Showing preview only.
                </p>
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-gray-500">
              <svg className="w-12 h-12 mx-auto mb-3 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="text-sm font-medium">No content available</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
