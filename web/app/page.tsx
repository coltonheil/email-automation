'use client';

import { useState, useEffect } from 'react';
import EmailList from '@/components/EmailList';
import EmailView from '@/components/EmailView';
import Sidebar from '@/components/Sidebar';
import TopBar from '@/components/TopBar';
import DashboardLayout from '@/components/DashboardLayout';

export default function HomePage() {
  const [selectedEmail, setSelectedEmail] = useState<any>(null);
  const [emails, setEmails] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState('all');
  const [lastFetch, setLastFetch] = useState<string | null>(null);

  useEffect(() => {
    fetchEmails();
  }, []);

  const fetchEmails = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 35000); // 35 second frontend timeout
      
      const response = await fetch('/api/emails?mode=unread&limit=20', {
        signal: controller.signal,
      });
      
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }
      
      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to fetch emails');
      }
      
      setEmails(data.emails || []);
      setLastFetch(new Date().toLocaleTimeString());
      setError(null);
    } catch (error: any) {
      console.error('Failed to fetch emails:', error);
      
      if (error.name === 'AbortError') {
        setError('Request timed out. The server is taking too long to respond.');
      } else {
        setError(error.message || 'Failed to fetch emails. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const filteredEmails = emails.filter(email => {
    if (filter === 'all') return true;
    if (filter === 'unread') return email.is_unread;
    if (filter === 'urgent') return email.priority_category === 'urgent';
    if (filter === 'normal') return email.priority_category === 'normal';
    if (filter === 'low') return email.priority_category === 'low';
    return true;
  });

  return (
    <DashboardLayout>
      <div className="flex flex-col h-full bg-gray-50">
        {/* Top Bar */}
        <TopBar 
          onRefresh={fetchEmails} 
          loading={loading}
          lastFetch={lastFetch}
        />

      {/* Error Banner */}
      {error && (
        <div className="bg-red-50 border-b border-red-200 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <svg className="w-5 h-5 text-red-600" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <div>
              <p className="text-sm font-medium text-red-900">{error}</p>
              <p className="text-xs text-red-700 mt-0.5">
                Showing {emails.length} cached emails from last successful sync.
              </p>
            </div>
          </div>
          <button
            onClick={() => setError(null)}
            className="text-red-600 hover:text-red-800 transition-colors"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        </div>
      )}

      {/* Main 3-Column Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <Sidebar 
          filter={filter} 
          setFilter={setFilter}
          emailCounts={{
            all: emails.length,
            unread: emails.filter(e => e.is_unread).length,
            urgent: emails.filter(e => e.priority_category === 'urgent').length,
            normal: emails.filter(e => e.priority_category === 'normal').length,
            low: emails.filter(e => e.priority_category === 'low').length,
          }}
        />

        {/* Email List */}
        <div className="w-96 border-r border-gray-200 overflow-hidden flex flex-col">
          <EmailList 
            emails={filteredEmails}
            selectedEmail={selectedEmail}
            onSelectEmail={setSelectedEmail}
            loading={loading}
          />
        </div>

        {/* Reading Pane */}
        <div className="flex-1 overflow-hidden">
          {selectedEmail ? (
            <EmailView email={selectedEmail} />
          ) : (
            <div className="h-full flex items-center justify-center bg-white">
              <div className="text-center">
                <svg 
                  className="mx-auto h-16 w-16 text-gray-300 mb-4" 
                  fill="none" 
                  viewBox="0 0 24 24" 
                  stroke="currentColor"
                  strokeWidth={1.5}
                >
                  <path 
                    strokeLinecap="round" 
                    strokeLinejoin="round" 
                    d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" 
                  />
                </svg>
                <h3 className="text-sm font-medium text-gray-900 mb-1">No email selected</h3>
                <p className="text-xs text-gray-500">Choose an email from the list to read</p>
              </div>
            </div>
          )}
        </div>
      </div>
      </div>
    </DashboardLayout>
  );
}
