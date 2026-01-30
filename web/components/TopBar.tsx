interface TopBarProps {
  onRefresh: () => void;
  loading: boolean;
  lastFetch?: string | null;
}

export default function TopBar({ onRefresh, loading, lastFetch }: TopBarProps) {
  return (
    <div className="h-12 bg-white border-b border-gray-200 px-4 flex items-center justify-between shadow-sm">
      {/* Left section - Sync button */}
      <div className="flex items-center gap-3">
        <button
          onClick={onRefresh}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100 rounded-md transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label="Refresh emails"
        >
          <svg 
            className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} 
            fill="none" 
            viewBox="0 0 24 24" 
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          <span className="font-medium">{loading ? 'Syncing...' : 'Sync'}</span>
        </button>

        {loading ? (
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <div className="w-1 h-1 bg-primary-600 rounded-full animate-pulse"></div>
            <span>Fetching emails from 8 accounts...</span>
          </div>
        ) : lastFetch ? (
          <div className="text-xs text-gray-500">
            Last synced: <span className="font-medium text-gray-700">{lastFetch}</span>
          </div>
        ) : null}
      </div>

      {/* Center section - Search */}
      <div className="flex-1 max-w-md mx-8">
        <div className="relative">
          <svg 
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" 
            fill="none" 
            viewBox="0 0 24 24" 
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            placeholder="Search emails..."
            className="w-full pl-10 pr-4 py-1.5 text-sm bg-gray-50 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all duration-150"
          />
        </div>
      </div>

      {/* Right section - Compose and settings */}
      <div className="flex items-center gap-2">
        <button className="btn btn-primary flex items-center gap-2">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
          </svg>
          <span>Compose</span>
        </button>
        
        <button 
          className="p-2 text-gray-600 hover:bg-gray-100 rounded-md transition-colors duration-150"
          aria-label="Settings"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>
      </div>
    </div>
  );
}
