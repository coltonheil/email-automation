# Email Automation - Web Dashboard

**Unified email inbox across 8 accounts with intelligent priority scoring.**

## Features

✅ **Unified Inbox** - All 8 email accounts in one view  
✅ **Priority Filtering** - Urgent, Normal, Low priority categories  
✅ **Modern UI** - Clean, professional email client interface  
✅ **Real-time Sync** - Fetch latest emails on demand  
✅ **Email Actions** - Read, reply, archive (coming soon)

## Quick Start

### Install Dependencies

```bash
npm install
```

### Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Build for Production

```bash
npm run build
npm start
```

## Architecture

- **Frontend:** Next.js 15 + React 19 + TypeScript + Tailwind CSS
- **Backend:** Next.js API routes (calls Python email fetcher)
- **Data:** Fetches from `../scripts/fetch_all_emails.py`

## API Routes

### `GET /api/emails`

Fetch emails from all accounts.

**Query Parameters:**
- `mode` - `unread`, `recent`, or `all` (default: `unread`)
- `limit` - Max emails per account (default: `100`)
- `hours` - Hours to look back for `mode=recent` (default: `24`)

**Example:**
```bash
curl http://localhost:3000/api/emails?mode=unread&limit=50
```

## Components

- **`Sidebar`** - Navigation and filters
- **`TopBar`** - Refresh and compose buttons
- **`EmailList`** - List of emails with priority badges
- **`EmailView`** - Full email reading pane

## Customization

### Priority Colors

Edit `components/EmailList.tsx` to customize priority colors:

```typescript
const getPriorityColor = (category: string) => {
  if (category === 'urgent') return 'border-l-red-500';
  if (category === 'normal') return 'border-l-blue-500';
  return 'border-l-gray-300';
};
```

### Styling

All styles use Tailwind CSS. Edit `tailwind.config.ts` to customize the design system.

## Next Steps

- [ ] Implement reply/compose functionality
- [ ] Add email search
- [ ] Add keyboard shortcuts
- [ ] Add email threading
- [ ] Integrate with Slack for urgent notifications
- [ ] Add LLM-powered auto-drafting

## License

Internal project - not for external distribution.
