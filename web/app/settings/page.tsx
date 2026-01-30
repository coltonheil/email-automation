'use client';

import { useState, useEffect } from 'react';
import DashboardLayout from '@/components/DashboardLayout';

interface SenderFilters {
  skip_drafting: {
    emails: string[];
    domains: string[];
    relationship_types: string[];
    reasons: Record<string, string>;
  };
  always_draft: {
    emails: string[];
    domains: string[];
    priority_threshold: number;
    reason: string;
  };
  override: {
    critical_keywords: string[];
    reason: string;
  };
}

export default function SettingsPage() {
  const [config, setConfig] = useState<SenderFilters | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  
  // Form state
  const [skipEmails, setSkipEmails] = useState('');
  const [skipDomains, setSkipDomains] = useState('');
  const [vipEmails, setVipEmails] = useState('');
  const [criticalKeywords, setCriticalKeywords] = useState('');
  const [priorityThreshold, setPriorityThreshold] = useState(90);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/settings');
      const data = await res.json();
      
      if (data.success) {
        setConfig(data.config);
        setSkipEmails(data.config.skip_drafting.emails.join('\n'));
        setSkipDomains(data.config.skip_drafting.domains.join('\n'));
        setVipEmails(data.config.always_draft.emails.join('\n'));
        setCriticalKeywords(data.config.override.critical_keywords.join('\n'));
        setPriorityThreshold(data.config.always_draft.priority_threshold);
      }
    } catch (error) {
      console.error('Error fetching settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!config) return;
    
    setSaving(true);
    setSaved(false);
    
    try {
      const updatedConfig: SenderFilters = {
        skip_drafting: {
          ...config.skip_drafting,
          emails: skipEmails.split('\n').filter(e => e.trim()),
          domains: skipDomains.split('\n').filter(d => d.trim()),
        },
        always_draft: {
          ...config.always_draft,
          emails: vipEmails.split('\n').filter(e => e.trim()),
          priority_threshold: priorityThreshold,
        },
        override: {
          ...config.override,
          critical_keywords: criticalKeywords.split('\n').filter(k => k.trim()),
        },
      };
      
      const res = await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatedConfig),
      });
      
      const data = await res.json();
      
      if (data.success) {
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
      }
    } catch (error) {
      console.error('Error saving settings:', error);
    } finally {
      setSaving(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="h-full flex flex-col bg-gray-50 overflow-auto">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold text-gray-900">Settings</h1>
              <p className="text-sm text-gray-500 mt-1">Configure sender filters and automation rules</p>
            </div>
            <button
              onClick={handleSave}
              disabled={saving || loading}
              className={`
                px-4 py-2 rounded-lg font-medium text-white transition-colors
                ${saved 
                  ? 'bg-green-600' 
                  : saving 
                    ? 'bg-gray-400 cursor-not-allowed' 
                    : 'bg-blue-600 hover:bg-blue-700'
                }
              `}
            >
              {saved ? '✓ Saved' : saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>

        {loading ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        ) : (
          <div className="p-6 space-y-6 max-w-4xl">
            {/* Skip Drafting Section */}
            <section className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-lg font-medium text-gray-900 mb-1">🚫 Skip Drafting</h2>
              <p className="text-sm text-gray-500 mb-4">
                Emails from these senders/domains will not get auto-drafts
              </p>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Email Patterns (one per line)
                  </label>
                  <p className="text-xs text-gray-500 mb-2">
                    Use wildcards: <code className="bg-gray-100 px-1 rounded">no-reply@*</code> or <code className="bg-gray-100 px-1 rounded">*@mailchimp.com</code>
                  </p>
                  <textarea
                    value={skipEmails}
                    onChange={(e) => setSkipEmails(e.target.value)}
                    rows={6}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="no-reply@*&#10;noreply@*&#10;newsletter@*"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Blocked Domains (one per line)
                  </label>
                  <p className="text-xs text-gray-500 mb-2">
                    Any email from these domains will be skipped
                  </p>
                  <textarea
                    value={skipDomains}
                    onChange={(e) => setSkipDomains(e.target.value)}
                    rows={4}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="mailchimp.com&#10;sendgrid.net&#10;klaviyo.com"
                  />
                </div>
              </div>
            </section>

            {/* VIP / Always Draft Section */}
            <section className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-lg font-medium text-gray-900 mb-1">⭐ VIP Senders (Always Draft)</h2>
              <p className="text-sm text-gray-500 mb-4">
                These senders will always get auto-drafts, regardless of other filters
              </p>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    VIP Email Patterns (one per line)
                  </label>
                  <textarea
                    value={vipEmails}
                    onChange={(e) => setVipEmails(e.target.value)}
                    rows={4}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="*@anthropic.com&#10;*@stripe.com&#10;ceo@yourcompany.com"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Priority Threshold
                  </label>
                  <p className="text-xs text-gray-500 mb-2">
                    Emails with priority score above this threshold will always get drafts
                  </p>
                  <div className="flex items-center gap-4">
                    <input
                      type="range"
                      min={50}
                      max={100}
                      value={priorityThreshold}
                      onChange={(e) => setPriorityThreshold(parseInt(e.target.value))}
                      className="flex-1"
                    />
                    <span className="text-sm font-medium text-gray-700 w-12">{priorityThreshold}</span>
                  </div>
                </div>
              </div>
            </section>

            {/* Critical Keywords Section */}
            <section className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-lg font-medium text-gray-900 mb-1">🚨 Critical Keywords (Override)</h2>
              <p className="text-sm text-gray-500 mb-4">
                Emails containing these keywords will bypass skip filters
              </p>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Keywords (one per line)
                </label>
                <textarea
                  value={criticalKeywords}
                  onChange={(e) => setCriticalKeywords(e.target.value)}
                  rows={4}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="urgent&#10;critical&#10;emergency&#10;asap"
                />
              </div>
            </section>

            {/* Current Stats */}
            <section className="bg-blue-50 rounded-lg border border-blue-200 p-6">
              <h2 className="text-lg font-medium text-blue-900 mb-2">📊 Current Filter Stats</h2>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <p className="text-blue-600 font-medium">{skipEmails.split('\n').filter(e => e.trim()).length}</p>
                  <p className="text-blue-700">Skip email patterns</p>
                </div>
                <div>
                  <p className="text-blue-600 font-medium">{skipDomains.split('\n').filter(d => d.trim()).length}</p>
                  <p className="text-blue-700">Blocked domains</p>
                </div>
                <div>
                  <p className="text-blue-600 font-medium">{vipEmails.split('\n').filter(e => e.trim()).length}</p>
                  <p className="text-blue-700">VIP patterns</p>
                </div>
              </div>
            </section>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
