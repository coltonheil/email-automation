'use client';

import { useState, useEffect } from 'react';
import DashboardLayout from '@/components/DashboardLayout';

interface Draft {
  id: number;
  email_id: number;
  draft_text: string;
  edited_text: string | null;
  model_used: string;
  status: string;
  created_at: string;
  approved_at: string | null;
  rejected_at: string | null;
  rejection_reason: string | null;
  sent_at: string | null;
  feedback_score: number | null;
  subject: string;
  from_email: string;
  from_name: string;
  priority_score: number;
  priority_category: string;
}

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
  sent: 'bg-blue-100 text-blue-800',
};

export default function DraftsPage() {
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [selectedDraft, setSelectedDraft] = useState<Draft | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [editedText, setEditedText] = useState('');

  useEffect(() => {
    fetchDrafts();
  }, [selectedStatus]);

  const fetchDrafts = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (selectedStatus !== 'all') params.set('status', selectedStatus);
      params.set('limit', '100');
      
      const res = await fetch(`/api/drafts?${params}`);
      const data = await res.json();
      
      if (data.success) {
        setDrafts(data.drafts);
        setCounts(data.counts);
      }
    } catch (error) {
      console.error('Error fetching drafts:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAction = async (action: string, extraData: Record<string, any> = {}) => {
    if (!selectedDraft) return;
    
    setActionLoading(true);
    try {
      const res = await fetch(`/api/drafts/${selectedDraft.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, ...extraData }),
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
          <h1 className="text-xl font-semibold text-gray-900">Drafts</h1>
          <p className="text-sm text-gray-500 mt-1">Review and manage generated email drafts</p>
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
                    ? 'border-blue-600 text-blue-600' 
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                  }
                `}
              >
                {tab.label}
                <span className={`
                  ml-2 px-2 py-0.5 rounded-full text-xs
                  ${selectedStatus === tab.id ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-500'}
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
          <div className="w-1/2 border-r border-gray-200 overflow-auto">
            {loading ? (
              <div className="flex items-center justify-center h-32">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              </div>
            ) : drafts.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-32 text-gray-500">
                <svg className="w-12 h-12 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p>No drafts found</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-100">
                {drafts.map(draft => (
                  <button
                    key={draft.id}
                    onClick={() => {
                      setSelectedDraft(draft);
                      setEditedText(draft.edited_text || draft.draft_text);
                      setEditMode(false);
                    }}
                    className={`
                      w-full px-4 py-3 text-left hover:bg-gray-50 transition-colors
                      ${selectedDraft?.id === draft.id ? 'bg-blue-50' : ''}
                    `}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          Re: {draft.subject}
                        </p>
                        <p className="text-xs text-gray-500 mt-0.5 truncate">
                          To: {draft.from_name || draft.from_email}
                        </p>
                        <p className="text-xs text-gray-400 mt-1 line-clamp-2">
                          {draft.draft_text.slice(0, 100)}...
                        </p>
                      </div>
                      <div className="flex flex-col items-end gap-1">
                        <span className={`
                          px-2 py-0.5 rounded text-xs font-medium
                          ${statusColors[draft.status] || 'bg-gray-100 text-gray-800'}
                        `}>
                          {draft.status}
                        </span>
                        {draft.feedback_score && (
                          <span className="text-xs text-yellow-600">
                            {'⭐'.repeat(draft.feedback_score)}
                          </span>
                        )}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Draft Detail */}
          <div className="flex-1 overflow-auto">
            {selectedDraft ? (
              <div className="p-6">
                {/* Header */}
                <div className="mb-4">
                  <div className="flex items-center justify-between mb-2">
                    <h2 className="text-lg font-medium text-gray-900">
                      Re: {selectedDraft.subject}
                    </h2>
                    <span className={`
                      px-3 py-1 rounded-full text-sm font-medium
                      ${statusColors[selectedDraft.status]}
                    `}>
                      {selectedDraft.status}
                    </span>
                  </div>
                  <p className="text-sm text-gray-500">
                    To: {selectedDraft.from_name} &lt;{selectedDraft.from_email}&gt;
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    Generated: {new Date(selectedDraft.created_at).toLocaleString()} · Model: {selectedDraft.model_used}
                  </p>
                </div>

                {/* Draft Content */}
                <div className="mb-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-medium text-gray-700">Draft Response</h3>
                    {selectedDraft.status === 'pending' && (
                      <button
                        onClick={() => setEditMode(!editMode)}
                        className="text-sm text-blue-600 hover:text-blue-700"
                      >
                        {editMode ? 'Cancel Edit' : 'Edit Draft'}
                      </button>
                    )}
                  </div>
                  {editMode ? (
                    <textarea
                      value={editedText}
                      onChange={(e) => setEditedText(e.target.value)}
                      className="w-full h-64 p-4 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  ) : (
                    <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-700 whitespace-pre-wrap">
                      {selectedDraft.edited_text || selectedDraft.draft_text}
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
                  <div className="flex gap-2">
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(selectedDraft.edited_text || selectedDraft.draft_text);
                        alert('Draft copied to clipboard!');
                      }}
                      className="flex-1 bg-gray-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-gray-700"
                    >
                      📋 Copy to Clipboard
                    </button>
                    <button
                      onClick={() => handleAction('sent', { via: 'manual' })}
                      disabled={actionLoading}
                      className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50"
                    >
                      ✓ Mark as Sent
                    </button>
                  </div>
                )}

                {/* Rating */}
                {(selectedDraft.status === 'sent' || selectedDraft.status === 'approved') && (
                  <div className="mt-4 pt-4 border-t border-gray-200">
                    <h3 className="text-sm font-medium text-gray-700 mb-2">Rate Draft Quality</h3>
                    <div className="flex gap-2">
                      {[1, 2, 3, 4, 5].map(score => (
                        <button
                          key={score}
                          onClick={() => handleAction('rate', { score })}
                          className={`
                            w-10 h-10 rounded-lg text-lg transition-colors
                            ${selectedDraft.feedback_score === score 
                              ? 'bg-yellow-400 text-white' 
                              : 'bg-gray-100 hover:bg-yellow-100'
                            }
                          `}
                        >
                          ⭐
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="h-full flex items-center justify-center text-gray-400">
                <div className="text-center">
                  <svg className="mx-auto h-12 w-12 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
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
