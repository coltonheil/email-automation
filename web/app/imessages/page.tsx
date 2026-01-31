'use client';

import { useState, useEffect } from 'react';
import DashboardLayout from '@/components/DashboardLayout';

interface iMessageDraft {
  id: number;
  imessage_id: number;
  draft_text: string;
  status: string;
  created_at: string;
  approved_at: string | null;
  rejected_at: string | null;
  sent_at: string | null;
  sender: string;
  chat: string | null;
  original_text: string;
  message_received_at: string;
}

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
  sent: 'bg-blue-100 text-blue-800',
};

export default function iMessagesPage() {
  const [drafts, setDrafts] = useState<iMessageDraft[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [selectedDraft, setSelectedDraft] = useState<iMessageDraft | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [editedText, setEditedText] = useState('');
  const [needsAccess, setNeedsAccess] = useState(false);

  useEffect(() => {
    fetchDrafts();
  }, [selectedStatus]);

  const fetchDrafts = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('view', 'drafts');
      if (selectedStatus !== 'all') params.set('status', selectedStatus);
      params.set('limit', '100');
      
      const res = await fetch(`/api/imessages?${params}`);
      const data = await res.json();
      
      if (data.success) {
        setDrafts(data.drafts || []);
        setCounts(data.counts || {});
      }
    } catch (error) {
      console.error('Error fetching iMessage drafts:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAction = async (action: string, extraData: Record<string, any> = {}) => {
    if (!selectedDraft) return;
    
    setActionLoading(true);
    try {
      const res = await fetch('/api/imessages', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: selectedDraft.id, action, ...extraData }),
      });
      
      const data = await res.json();
      
      if (data.success) {
        fetchDrafts();
        setSelectedDraft(null);
        setEditMode(false);
      }
    } catch (error) {
      console.error('Error performing action:', error);
    } finally {
      setActionLoading(false);
    }
  };

  const tabs = [
    { id: 'all', label: 'All', count: Object.values(counts).reduce((a, b) => a + b, 0) },
    { id: 'pending', label: 'Pending', count: counts.pending || 0 },
    { id: 'approved', label: 'Approved', count: counts.approved || 0 },
    { id: 'rejected', label: 'Rejected', count: counts.rejected || 0 },
    { id: 'sent', label: 'Sent', count: counts.sent || 0 },
  ];

  return (
    <DashboardLayout>
      <div className="h-full flex flex-col bg-white">
        {/* Header */}
        <div className="border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold text-gray-900">iMessage Drafts</h1>
              <p className="text-sm text-gray-500 mt-1">Review and manage iMessage draft responses</p>
            </div>
            <div className="bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              <p className="text-xs text-red-700 font-medium">⛔ DRAFT ONLY - No auto-send</p>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200 px-6">
          <div className="flex gap-6">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setSelectedStatus(tab.id)}
                className={`
                  py-3 text-sm font-medium border-b-2 transition-colors
                  ${selectedStatus === tab.id 
                    ? 'border-green-600 text-green-600' 
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                  }
                `}
              >
                {tab.label}
                <span className={`
                  ml-2 px-2 py-0.5 rounded-full text-xs
                  ${selectedStatus === tab.id ? 'bg-green-100 text-green-600' : 'bg-gray-100 text-gray-500'}
                `}>
                  {tab.count}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Draft List */}
          <div className="w-1/3 border-r border-gray-200 overflow-auto">
            {loading ? (
              <div className="flex items-center justify-center h-32">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600"></div>
              </div>
            ) : drafts.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-64 text-gray-500 p-6">
                <svg className="w-16 h-16 mb-4 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                <p className="font-medium">No iMessage drafts yet</p>
                <p className="text-sm text-center mt-2">
                  Drafts will appear here when unread iMessages are processed.
                </p>
                <div className="mt-4 p-3 bg-amber-50 rounded-lg border border-amber-200">
                  <p className="text-xs text-amber-800">
                    <strong>Setup required:</strong> Grant Full Disk Access to Terminal to read Messages.
                  </p>
                </div>
              </div>
            ) : (
              <div className="divide-y divide-gray-100">
                {drafts.map(draft => (
                  <button
                    key={draft.id}
                    onClick={() => {
                      setSelectedDraft(draft);
                      setEditedText(draft.draft_text);
                      setEditMode(false);
                    }}
                    className={`
                      w-full px-4 py-3 text-left hover:bg-gray-50 transition-colors
                      ${selectedDraft?.id === draft.id ? 'bg-green-50' : ''}
                    `}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {draft.sender}
                        </p>
                        <p className="text-xs text-gray-400 mt-1 line-clamp-2">
                          {draft.original_text?.slice(0, 60)}...
                        </p>
                      </div>
                      <span className={`
                        px-2 py-0.5 rounded text-xs font-medium shrink-0
                        ${statusColors[draft.status] || 'bg-gray-100 text-gray-800'}
                      `}>
                        {draft.status}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Draft Detail */}
          <div className="flex-1 overflow-auto">
            {selectedDraft ? (
              <div className="p-6 space-y-6">
                {/* Header */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h2 className="text-lg font-medium text-gray-900">
                      Reply to {selectedDraft.sender}
                    </h2>
                    <span className={`
                      px-3 py-1 rounded-full text-sm font-medium
                      ${statusColors[selectedDraft.status]}
                    `}>
                      {selectedDraft.status}
                    </span>
                  </div>
                  <p className="text-xs text-gray-400">
                    Received: {selectedDraft.message_received_at ? new Date(selectedDraft.message_received_at).toLocaleString() : 'Unknown'}
                  </p>
                </div>

                {/* Original Message */}
                <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                  <h3 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                    Original Message
                  </h3>
                  <p className="text-sm text-gray-700 whitespace-pre-wrap">
                    {selectedDraft.original_text}
                  </p>
                </div>

                {/* Draft Response */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-medium text-gray-700">Your Draft Response</h3>
                    {selectedDraft.status === 'pending' && (
                      <button
                        onClick={() => setEditMode(!editMode)}
                        className="text-sm text-blue-600 hover:text-blue-700"
                      >
                        {editMode ? 'Cancel' : 'Edit'}
                      </button>
                    )}
                  </div>
                  {editMode ? (
                    <textarea
                      value={editedText}
                      onChange={(e) => setEditedText(e.target.value)}
                      className="w-full h-40 p-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500"
                    />
                  ) : (
                    <div className="bg-green-50 rounded-lg p-4 text-sm text-gray-700 whitespace-pre-wrap border border-green-100">
                      {selectedDraft.draft_text}
                    </div>
                  )}
                </div>

                {/* Actions */}
                {selectedDraft.status === 'pending' && (
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleAction('approve')}
                      disabled={actionLoading}
                      className="flex-1 bg-green-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-green-700 disabled:opacity-50"
                    >
                      ✓ Approve
                    </button>
                    <button
                      onClick={() => {
                        const reason = prompt('Rejection reason:');
                        if (reason) handleAction('reject', { reason });
                      }}
                      disabled={actionLoading}
                      className="flex-1 bg-red-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-red-700 disabled:opacity-50"
                    >
                      ✗ Reject
                    </button>
                    {editMode && editedText !== selectedDraft.draft_text && (
                      <button
                        onClick={() => handleAction('edit', { text: editedText })}
                        disabled={actionLoading}
                        className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50"
                      >
                        Save Edit
                      </button>
                    )}
                  </div>
                )}

                {selectedDraft.status === 'approved' && !selectedDraft.sent_at && (
                  <div className="space-y-3">
                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                      <p className="text-sm text-amber-800">
                        <strong>⚠️ Manual send required:</strong> Copy the draft above and paste it in Messages.app to send.
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => {
                          navigator.clipboard.writeText(selectedDraft.draft_text);
                          alert('Draft copied to clipboard! Open Messages.app to send.');
                        }}
                        className="flex-1 bg-gray-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-gray-700"
                      >
                        📋 Copy to Clipboard
                      </button>
                      <button
                        onClick={() => handleAction('sent')}
                        disabled={actionLoading}
                        className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50"
                      >
                        ✓ Mark as Sent
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="h-full flex items-center justify-center text-gray-400">
                <div className="text-center">
                  <svg className="mx-auto h-12 w-12 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                  <p className="text-sm">Select a draft to view details</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
