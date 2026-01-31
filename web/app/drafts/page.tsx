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
  body?: string;
  snippet?: string;
  priority_score: number;
  priority_category: string;
  received_at?: string;
}

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
  sent: 'bg-blue-100 text-blue-800',
};

// Simple HTML to text converter
function stripHtml(html: string): string {
  if (!html) return '';
  return html
    .replace(/<script[^>]*>.*?<\/script>/gi, '')
    .replace(/<style[^>]*>.*?<\/style>/gi, '')
    .replace(/<[^>]+>/g, '\n')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/\n\s*\n+/g, '\n\n')
    .trim();
}

export default function DraftsPage() {
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [selectedDraft, setSelectedDraft] = useState<Draft | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [editedText, setEditedText] = useState('');
  
  // AI Edit modal state
  const [showAiEdit, setShowAiEdit] = useState(false);
  const [aiInstruction, setAiInstruction] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  
  // Show original email toggle
  const [showOriginal, setShowOriginal] = useState(true);

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

  const fetchDraftDetails = async (draftId: number) => {
    try {
      const res = await fetch(`/api/drafts/${draftId}`);
      const data = await res.json();
      if (data.success && data.draft) {
        setSelectedDraft(data.draft);
        setEditedText(data.draft.edited_text || data.draft.draft_text);
        setEditMode(false);
      }
    } catch (error) {
      console.error('Error fetching draft details:', error);
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
        if (selectedDraft) {
          fetchDraftDetails(selectedDraft.id);
        }
      }
    } catch (error) {
      console.error('Error performing action:', error);
    } finally {
      setActionLoading(false);
    }
  };

  const handleAiEdit = async () => {
    if (!selectedDraft || !aiInstruction.trim()) return;
    
    setAiLoading(true);
    try {
      // Queue the AI edit request
      const res = await fetch(`/api/drafts/${selectedDraft.id}/ai-edit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instruction: aiInstruction }),
      });
      
      const data = await res.json();
      
      if (data.success && data.queued) {
        // Poll for completion
        const queueId = data.queue_id;
        let attempts = 0;
        const maxAttempts = 60; // 60 seconds max
        
        const pollForResult = async () => {
          attempts++;
          const pollRes = await fetch(`/api/drafts/${selectedDraft.id}/ai-edit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ poll_queue_id: queueId }),
          });
          
          const pollData = await pollRes.json();
          
          if (pollData.completed) {
            if (pollData.success && pollData.newDraftText) {
              // Update the selected draft with new text
              setSelectedDraft({
                ...selectedDraft,
                edited_text: pollData.newDraftText,
              });
              setEditedText(pollData.newDraftText);
              setShowAiEdit(false);
              setAiInstruction('');
              fetchDrafts();
            } else {
              alert(`Error: ${pollData.error || 'AI edit failed'}`);
            }
            setAiLoading(false);
          } else if (attempts < maxAttempts) {
            // Keep polling
            setTimeout(pollForResult, 1000);
          } else {
            alert('AI edit timed out. Check back later or try again.');
            setAiLoading(false);
          }
        };
        
        // Start polling after a short delay
        setTimeout(pollForResult, 1000);
        
      } else if (data.success && data.newDraftText) {
        // Immediate result (shouldn't happen with queue, but handle it)
        setSelectedDraft({
          ...selectedDraft,
          edited_text: data.newDraftText,
        });
        setEditedText(data.newDraftText);
        setShowAiEdit(false);
        setAiInstruction('');
        fetchDrafts();
        setAiLoading(false);
      } else {
        alert(`Error: ${data.error || 'Failed to queue edit'}`);
        setAiLoading(false);
      }
    } catch (error) {
      console.error('Error requesting AI edit:', error);
      alert('Error processing AI edit request');
      setAiLoading(false);
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
          <div className="w-1/3 border-r border-gray-200 overflow-auto">
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
                    onClick={() => fetchDraftDetails(draft.id)}
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
                          {draft.draft_text.slice(0, 80)}...
                        </p>
                      </div>
                      <div className="flex flex-col items-end gap-1">
                        <span className={`
                          px-2 py-0.5 rounded text-xs font-medium
                          ${statusColors[draft.status] || 'bg-gray-100 text-gray-800'}
                        `}>
                          {draft.status}
                        </span>
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
              <div className="p-6 space-y-6">
                {/* Header */}
                <div>
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

                {/* Original Email Section */}
                <div className="border border-gray-200 rounded-lg overflow-hidden">
                  <button
                    onClick={() => setShowOriginal(!showOriginal)}
                    className="w-full px-4 py-3 bg-gray-50 flex items-center justify-between hover:bg-gray-100 transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                      </svg>
                      <span className="font-medium text-gray-700">Original Email</span>
                      <span className="text-xs text-gray-500">
                        (from {selectedDraft.from_name})
                      </span>
                    </div>
                    <svg 
                      className={`w-5 h-5 text-gray-400 transition-transform ${showOriginal ? 'rotate-180' : ''}`} 
                      fill="none" 
                      viewBox="0 0 24 24" 
                      stroke="currentColor"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                  {showOriginal && (
                    <div className="p-4 bg-white border-t border-gray-200">
                      <div className="text-xs text-gray-500 mb-2">
                        <strong>Subject:</strong> {selectedDraft.subject}
                      </div>
                      {selectedDraft.received_at && (
                        <div className="text-xs text-gray-500 mb-3">
                          <strong>Received:</strong> {new Date(selectedDraft.received_at).toLocaleString()}
                        </div>
                      )}
                      <div className="text-sm text-gray-700 whitespace-pre-wrap max-h-64 overflow-auto bg-gray-50 p-3 rounded border">
                        {selectedDraft.body 
                          ? stripHtml(selectedDraft.body).slice(0, 2000) + (stripHtml(selectedDraft.body).length > 2000 ? '...' : '')
                          : selectedDraft.snippet || '(No content)'}
                      </div>
                    </div>
                  )}
                </div>

                {/* Draft Content */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-medium text-gray-700">Your Draft Response</h3>
                    <div className="flex gap-2">
                      {selectedDraft.status === 'pending' && (
                        <>
                          <button
                            onClick={() => setShowAiEdit(true)}
                            className="text-sm text-purple-600 hover:text-purple-700 flex items-center gap-1 px-3 py-1 rounded-md bg-purple-50 hover:bg-purple-100"
                          >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                            Edit with AI
                          </button>
                          <button
                            onClick={() => setEditMode(!editMode)}
                            className="text-sm text-blue-600 hover:text-blue-700 px-3 py-1 rounded-md bg-blue-50 hover:bg-blue-100"
                          >
                            {editMode ? 'Cancel' : 'Manual Edit'}
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                  {editMode ? (
                    <textarea
                      value={editedText}
                      onChange={(e) => setEditedText(e.target.value)}
                      className="w-full h-64 p-4 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono"
                    />
                  ) : (
                    <div className="bg-blue-50 rounded-lg p-4 text-sm text-gray-700 whitespace-pre-wrap border border-blue-100">
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
                    {editMode && editedText !== (selectedDraft.edited_text || selectedDraft.draft_text) && (
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

      {/* AI Edit Modal */}
      {showAiEdit && selectedDraft && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Edit with AI</h3>
                <p className="text-sm text-gray-500">Ask Opus to modify your draft</p>
              </div>
              <button
                onClick={() => setShowAiEdit(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            <div className="p-6 space-y-4 overflow-auto max-h-[60vh]">
              {/* Current Draft Preview */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Current Draft</label>
                <div className="bg-gray-50 rounded-lg p-3 text-sm text-gray-600 max-h-32 overflow-auto">
                  {(selectedDraft.edited_text || selectedDraft.draft_text).slice(0, 300)}
                  {(selectedDraft.edited_text || selectedDraft.draft_text).length > 300 && '...'}
                </div>
              </div>
              
              {/* Instruction Input */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  What would you like to change?
                </label>
                <textarea
                  value={aiInstruction}
                  onChange={(e) => setAiInstruction(e.target.value)}
                  placeholder="e.g., Make it shorter and more direct, add a question about their timeline, make the tone more formal..."
                  className="w-full h-32 p-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                />
              </div>
              
              {/* Quick Actions */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Quick Edits</label>
                <div className="flex flex-wrap gap-2">
                  {[
                    'Make it shorter',
                    'Make it more formal',
                    'Make it friendlier',
                    'Add a question',
                    'Add a call to action',
                    'Simplify the language',
                  ].map((suggestion) => (
                    <button
                      key={suggestion}
                      onClick={() => setAiInstruction(suggestion)}
                      className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded-full text-gray-700"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            
            <div className="px-6 py-4 border-t border-gray-200 flex gap-3 justify-end">
              <button
                onClick={() => setShowAiEdit(false)}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
              >
                Cancel
              </button>
              <button
                onClick={handleAiEdit}
                disabled={aiLoading || !aiInstruction.trim()}
                className="px-6 py-2 bg-purple-600 text-white text-sm font-medium rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {aiLoading ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
                    Processing...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                    Update Draft
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
