'use client';

import { useState, useEffect } from 'react';
import EmailList from '@/components/EmailList';
import EmailView from '@/components/EmailView';
import Sidebar from '@/components/Sidebar';
import TopBar from '@/components/TopBar';

export default function HomePage() {
  const [selectedEmail, setSelectedEmail] = useState<any>(null);
  const [emails, setEmails] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all'); // all, urgent, normal, low, unread

  useEffect(() => {
    fetchEmails();
  }, []);

  const fetchEmails = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/emails?mode=unread&limit=100');
      const data = await response.json();
      setEmails(data.emails || []);
    } catch (error) {
      console.error('Failed to fetch emails:', error);
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
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Top Bar */}
      <TopBar onRefresh={fetchEmails} loading={loading} />

      {/* Main 3-Column Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar - Fixed width */}
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

        {/* Email List - Fixed width */}
        <div className="w-96 border-r border-gray-200 overflow-hidden flex flex-col">
          <EmailList 
            emails={filteredEmails}
            selectedEmail={selectedEmail}
            onSelectEmail={setSelectedEmail}
            loading={loading}
          />
        </div>

        {/* Reading Pane - Flexible width */}
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
  );
}
