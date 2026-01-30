'use client';

import { useState, useEffect } from 'react';
import DashboardLayout from '@/components/DashboardLayout';

interface Analytics {
  period: {
    days: number;
    from: string;
    to: string;
  };
  emails: {
    total_emails: number;
    unread_emails: number;
    urgent_emails: number;
    normal_emails: number;
    low_emails: number;
    avg_priority: number;
    per_day: { date: string; count: number }[];
  };
  drafts: {
    total_drafts: number;
    pending_drafts: number;
    approved_drafts: number;
    rejected_drafts: number;
    sent_drafts: number;
    acceptance_rate: number;
    avg_rating: number;
    per_day: { date: string; count: number }[];
  };
  api: {
    total_calls: number;
    claude_calls: number;
    composio_calls: number;
    total_tokens: number;
    total_cost: number;
  };
  top_senders: { email: string; name: string; email_count: number; avg_priority: number }[];
  priority_distribution: { category: string; count: number }[];
}

function StatCard({ title, value, subtitle, color = 'blue' }: { 
  title: string; 
  value: string | number; 
  subtitle?: string;
  color?: string;
}) {
  const colorClasses: Record<string, string> = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    yellow: 'bg-yellow-50 text-yellow-600',
    red: 'bg-red-50 text-red-600',
    purple: 'bg-purple-50 text-purple-600',
  };
  
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <p className="text-sm text-gray-500">{title}</p>
      <p className={`text-2xl font-semibold mt-1 ${colorClasses[color]?.split(' ')[1] || 'text-gray-900'}`}>
        {value}
      </p>
      {subtitle && (
        <p className="text-xs text-gray-400 mt-1">{subtitle}</p>
      )}
    </div>
  );
}

function SimpleBarChart({ data, label }: { data: { date: string; count: number }[]; label: string }) {
  if (!data || data.length === 0) {
    return <div className="h-32 flex items-center justify-center text-gray-400">No data</div>;
  }
  
  const maxCount = Math.max(...data.map(d => d.count), 1);
  
  return (
    <div className="h-32 flex items-end gap-1">
      {data.map((d, i) => (
        <div key={i} className="flex-1 flex flex-col items-center gap-1">
          <div 
            className="w-full bg-blue-500 rounded-t transition-all"
            style={{ height: `${(d.count / maxCount) * 100}%`, minHeight: d.count > 0 ? '4px' : '0' }}
            title={`${d.date}: ${d.count} ${label}`}
          />
          <span className="text-xs text-gray-400 -rotate-45 origin-top-left">
            {new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function AnalyticsPage() {
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(7);

  useEffect(() => {
    fetchAnalytics();
  }, [days]);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/analytics?days=${days}`);
      const data = await res.json();
      
      if (data.success) {
        setAnalytics(data);
      }
    } catch (error) {
      console.error('Error fetching analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="h-full flex flex-col bg-gray-50 overflow-auto">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold text-gray-900">Analytics</h1>
              <p className="text-sm text-gray-500 mt-1">Usage statistics and performance metrics</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500">Period:</span>
              <select
                value={days}
                onChange={(e) => setDays(parseInt(e.target.value))}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
              >
                <option value={7}>Last 7 days</option>
                <option value={14}>Last 14 days</option>
                <option value={30}>Last 30 days</option>
                <option value={90}>Last 90 days</option>
              </select>
            </div>
          </div>
        </div>

        {loading || !analytics ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        ) : (
          <div className="p-6 space-y-6">
            {/* Email Stats */}
            <section>
              <h2 className="text-lg font-medium text-gray-900 mb-4">📧 Email Statistics</h2>
              <div className="grid grid-cols-5 gap-4">
                <StatCard title="Total Emails" value={analytics.emails.total_emails} color="blue" />
                <StatCard title="Unread" value={analytics.emails.unread_emails} color="yellow" />
                <StatCard title="Urgent" value={analytics.emails.urgent_emails} color="red" />
                <StatCard title="Normal" value={analytics.emails.normal_emails} color="green" />
                <StatCard title="Avg Priority" value={analytics.emails.avg_priority || 'N/A'} color="purple" />
              </div>
              <div className="mt-4 bg-white rounded-lg border border-gray-200 p-4">
                <h3 className="text-sm font-medium text-gray-700 mb-2">Emails per Day</h3>
                <SimpleBarChart data={analytics.emails.per_day} label="emails" />
              </div>
            </section>

            {/* Draft Stats */}
            <section>
              <h2 className="text-lg font-medium text-gray-900 mb-4">✍️ Draft Statistics</h2>
              <div className="grid grid-cols-5 gap-4">
                <StatCard title="Total Drafts" value={analytics.drafts.total_drafts} color="blue" />
                <StatCard title="Pending" value={analytics.drafts.pending_drafts} color="yellow" />
                <StatCard title="Approved" value={analytics.drafts.approved_drafts} color="green" />
                <StatCard title="Rejected" value={analytics.drafts.rejected_drafts} color="red" />
                <StatCard 
                  title="Acceptance Rate" 
                  value={`${analytics.drafts.acceptance_rate}%`} 
                  subtitle={analytics.drafts.avg_rating ? `Avg rating: ${analytics.drafts.avg_rating}/5` : undefined}
                  color="purple" 
                />
              </div>
              <div className="mt-4 bg-white rounded-lg border border-gray-200 p-4">
                <h3 className="text-sm font-medium text-gray-700 mb-2">Drafts per Day</h3>
                <SimpleBarChart data={analytics.drafts.per_day} label="drafts" />
              </div>
            </section>

            {/* API Usage */}
            <section>
              <h2 className="text-lg font-medium text-gray-900 mb-4">🔌 API Usage</h2>
              <div className="grid grid-cols-4 gap-4">
                <StatCard title="Total API Calls" value={analytics.api.total_calls} color="blue" />
                <StatCard title="Claude Calls" value={analytics.api.claude_calls} subtitle="Opus model" color="purple" />
                <StatCard title="Composio Calls" value={analytics.api.composio_calls} subtitle="Email fetching" color="green" />
                <StatCard 
                  title="Tokens Used" 
                  value={analytics.api.total_tokens.toLocaleString()} 
                  subtitle={analytics.api.total_cost > 0 ? `$${analytics.api.total_cost.toFixed(2)} est.` : undefined}
                  color="yellow" 
                />
              </div>
            </section>

            {/* Top Senders */}
            <section>
              <h2 className="text-lg font-medium text-gray-900 mb-4">👥 Top Senders</h2>
              <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Sender</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Emails</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Avg Priority</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {analytics.top_senders.map((sender, i) => (
                      <tr key={i}>
                        <td className="px-4 py-3">
                          <p className="text-sm font-medium text-gray-900">{sender.name || sender.email}</p>
                          {sender.name && <p className="text-xs text-gray-500">{sender.email}</p>}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600">{sender.email_count}</td>
                        <td className="px-4 py-3 text-sm text-gray-600">{sender.avg_priority}/100</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            {/* Priority Distribution */}
            <section>
              <h2 className="text-lg font-medium text-gray-900 mb-4">📊 Priority Distribution</h2>
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <div className="flex items-end gap-4 h-32">
                  {analytics.priority_distribution.map((item, i) => {
                    const total = analytics.priority_distribution.reduce((a, b) => a + b.count, 0);
                    const pct = total > 0 ? (item.count / total * 100).toFixed(1) : 0;
                    const colors: Record<string, string> = {
                      urgent: 'bg-red-500',
                      normal: 'bg-yellow-500',
                      low: 'bg-green-500',
                    };
                    return (
                      <div key={i} className="flex-1 flex flex-col items-center gap-2">
                        <span className="text-xs text-gray-500">{pct}%</span>
                        <div 
                          className={`w-full rounded-t ${colors[item.category] || 'bg-gray-400'}`}
                          style={{ height: `${total > 0 ? (item.count / total * 100) : 0}%`, minHeight: item.count > 0 ? '8px' : '0' }}
                        />
                        <span className="text-sm font-medium text-gray-700 capitalize">{item.category}</span>
                        <span className="text-xs text-gray-400">{item.count} emails</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </section>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
