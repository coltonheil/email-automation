'use client';

import { useState, useEffect } from 'react';
import DashboardLayout from '@/components/DashboardLayout';

interface Sender {
  email: string;
  name: string;
  total_emails_received: number;
  last_email_at: string;
  avg_priority_score: number;
  unread_count: number;
  urgent_count: number;
  drafts: {
    total_drafts: number;
    approved_drafts: number;
    rejected_drafts: number;
  };
}

export default function SendersPage() {
  const [senders, setSenders] = useState<Sender[]>([]);
  const [loading, setLoading] = useState(true);
  const [sort, setSort] = useState('recent');
  const [search, setSearch] = useState('');

  useEffect(() => {
    fetchSenders();
  }, [sort]);

  const fetchSenders = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/senders?sort=${sort}&limit=100`);
      const data = await res.json();
      
      if (data.success) {
        setSenders(data.senders);
      }
    } catch (error) {
      console.error('Error fetching senders:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredSenders = senders.filter(sender => 
    sender.email.toLowerCase().includes(search.toLowerCase()) ||
    (sender.name && sender.name.toLowerCase().includes(search.toLowerCase()))
  );

  const getPriorityColor = (score: number) => {
    if (score >= 80) return 'text-red-600 bg-red-50';
    if (score >= 60) return 'text-yellow-600 bg-yellow-50';
    return 'text-green-600 bg-green-50';
  };

  return (
    <DashboardLayout>
      <div className="h-full flex flex-col bg-white">
        {/* Header */}
        <div className="border-b border-gray-200 px-6 py-4">
          <h1 className="text-xl font-semibold text-gray-900">Senders</h1>
          <p className="text-sm text-gray-500 mt-1">Sender profiles and email history</p>
        </div>

        {/* Controls */}
        <div className="border-b border-gray-200 px-6 py-3 flex items-center gap-4">
          {/* Search */}
          <div className="flex-1 max-w-md">
            <div className="relative">
              <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                type="text"
                placeholder="Search senders..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>

          {/* Sort */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">Sort by:</span>
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
            >
              <option value="recent">Most Recent</option>
              <option value="count">Most Emails</option>
              <option value="priority">Highest Priority</option>
            </select>
          </div>
        </div>

        {/* Table */}
        <div className="flex-1 overflow-auto">
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : (
            <table className="w-full">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Sender
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Emails
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Priority
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Drafts
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Last Email
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-100">
                {filteredSenders.map((sender) => (
                  <tr key={sender.email} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-gray-200 rounded-full flex items-center justify-center text-sm font-medium text-gray-600">
                          {(sender.name || sender.email).charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-900">
                            {sender.name || '(No name)'}
                          </p>
                          <p className="text-xs text-gray-500">{sender.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-900">
                          {sender.total_emails_received}
                        </span>
                        {sender.unread_count > 0 && (
                          <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full">
                            {sender.unread_count} unread
                          </span>
                        )}
                        {sender.urgent_count > 0 && (
                          <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs rounded-full">
                            {sender.urgent_count} urgent
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`
                        px-2 py-1 rounded text-xs font-medium
                        ${getPriorityColor(sender.avg_priority_score)}
                      `}>
                        {sender.avg_priority_score}/100
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-1 text-xs">
                        {sender.drafts.total_drafts > 0 ? (
                          <>
                            <span className="text-gray-600">{sender.drafts.total_drafts} total</span>
                            {sender.drafts.approved_drafts > 0 && (
                              <span className="text-green-600">({sender.drafts.approved_drafts} ✓)</span>
                            )}
                            {sender.drafts.rejected_drafts > 0 && (
                              <span className="text-red-600">({sender.drafts.rejected_drafts} ✗)</span>
                            )}
                          </>
                        ) : (
                          <span className="text-gray-400">No drafts</span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {sender.last_email_at ? new Date(sender.last_email_at).toLocaleDateString() : 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Footer Stats */}
        <div className="border-t border-gray-200 px-6 py-3 bg-gray-50">
          <p className="text-sm text-gray-500">
            Showing {filteredSenders.length} of {senders.length} senders
          </p>
        </div>
      </div>
    </DashboardLayout>
  );
}
