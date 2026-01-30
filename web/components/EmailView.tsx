interface EmailViewProps {
  email: any;
}

export default function EmailView({ email }: EmailViewProps) {
  const getPriorityLabel = (category: string) => {
    if (category === 'urgent') return { text: 'Urgent', bg: 'bg-red-100', text_color: 'text-red-800' };
    if (category === 'normal') return { text: 'Normal', bg: 'bg-blue-100', text_color: 'text-blue-800' };
    return { text: 'Low Priority', bg: 'bg-gray-100', text_color: 'text-gray-800' };
  };

  const priority = getPriorityLabel(email.priority_category);

  return (
    <div className="h-full flex flex-col">
      {/* Email Header */}
      <div className="border-b border-gray-200 p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <h1 className="text-2xl font-semibold text-gray-900 mb-2">{email.subject}</h1>
            <div className="flex items-center gap-3 text-sm text-gray-600">
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${priority.bg} ${priority.text_color}`}>
                {priority.text} • {email.priority_score}
              </span>
              <span className="uppercase font-semibold">{email.provider}</span>
              {email.is_unread && (
                <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-medium">
                  Unread
                </span>
              )}
              {email.has_attachments && (
                <span className="text-gray-500">📎 Attachments</span>
              )}
            </div>
          </div>
        </div>

        <div className="space-y-2 text-sm">
          <div className="flex items-start">
            <span className="w-16 text-gray-500">From:</span>
            <span className="text-gray-900 font-medium">{email.from}</span>
          </div>
          <div className="flex items-start">
            <span className="w-16 text-gray-500">To:</span>
            <span className="text-gray-900">{email.to}</span>
          </div>
          {email.cc && (
            <div className="flex items-start">
              <span className="w-16 text-gray-500">CC:</span>
              <span className="text-gray-900">{email.cc}</span>
            </div>
          )}
          <div className="flex items-start">
            <span className="w-16 text-gray-500">Date:</span>
            <span className="text-gray-900">
              {new Date(email.received_at).toLocaleString()}
            </span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2 mt-4">
          <button className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors">
            ↩️ Reply
          </button>
          <button className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
            ↪️ Forward
          </button>
          <button className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
            🗑️ Archive
          </button>
          <button className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
            ✓ Mark Read
          </button>
        </div>
      </div>

      {/* Email Body */}
      <div className="flex-1 p-6 overflow-y-auto">
        <div className="prose prose-sm max-w-none">
          {email.body ? (
            <pre className="whitespace-pre-wrap font-sans text-gray-800 leading-relaxed">
              {email.body}
            </pre>
          ) : (
            <div className="text-gray-500 italic">
              <p>{email.snippet}</p>
              <p className="mt-4 text-xs">Full body not available</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
