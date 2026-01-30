# Email Client UI - Polish Plan (Outlook-Inspired)

**Goal:** Transform the email client into a polished, professional interface matching Microsoft Outlook's clean aesthetic.

---

## 1. Design System

### Color Palette

**Primary (Blue Accent):**
- `primary-50`: #EFF6FF (lightest blue - hover backgrounds)
- `primary-100`: #DBEAFE (selection backgrounds)
- `primary-200`: #BFDBFE (borders, dividers)
- `primary-500`: #3B82F6 (main blue - buttons, links, focus)
- `primary-600`: #2563EB (hover states)
- `primary-700`: #1D4ED8 (active states)

**Neutral Grays:**
- `gray-50`: #F9FAFB (page background)
- `gray-100`: #F3F4F6 (card backgrounds)
- `gray-200`: #E5E7EB (borders, dividers)
- `gray-300`: #D1D5DB (inactive elements)
- `gray-400`: #9CA3AF (secondary text)
- `gray-500`: #6B7280 (tertiary text)
- `gray-700`: #374151 (body text)
- `gray-900`: #111827 (headings, important text)

**Semantic Colors:**
- `urgent`: #EF4444 (red - urgent priority)
- `urgent-bg`: #FEF2F2 (light red background)
- `normal`: #3B82F6 (blue - normal priority)
- `normal-bg`: #EFF6FF (light blue background)
- `low`: #6B7280 (gray - low priority)
- `low-bg`: #F9FAFB (light gray background)
- `success`: #10B981 (green - actions)
- `warning`: #F59E0B (amber - alerts)

### Typography

**Font Family:**
- Primary: `'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`
- Monospace: `'SF Mono', 'Monaco', 'Courier New', monospace`

**Type Scale:**
- `xs`: 11px / 16px (metadata, timestamps)
- `sm`: 13px / 20px (body text, email snippets)
- `base`: 14px / 20px (default body)
- `lg`: 16px / 24px (email subjects)
- `xl`: 18px / 28px (section headers)
- `2xl`: 24px / 32px (page titles)

**Weights:**
- Regular: 400 (body text)
- Medium: 500 (emphasis, buttons)
- Semibold: 600 (headings, email subjects)
- Bold: 700 (priority labels)

### Spacing Scale

- `1`: 4px (tight spacing)
- `2`: 8px (compact spacing)
- `3`: 12px (default gaps)
- `4`: 16px (comfortable padding)
- `5`: 20px (section spacing)
- `6`: 24px (large gaps)
- `8`: 32px (section dividers)
- `10`: 40px (major sections)

### Shadows

- `sm`: 0 1px 2px rgba(0, 0, 0, 0.05) (subtle depth)
- `md`: 0 4px 6px rgba(0, 0, 0, 0.07) (cards, dropdowns)
- `lg`: 0 10px 15px rgba(0, 0, 0, 0.1) (modals, popovers)
- `focus`: 0 0 0 3px rgba(59, 130, 246, 0.15) (keyboard focus)

### Border Radius

- `sm`: 4px (small elements, badges)
- `md`: 6px (buttons, inputs)
- `lg`: 8px (cards, panels)
- `xl`: 12px (large containers)

---

## 2. Layout Architecture (3-Column Outlook-Style)

```
┌─────────────────────────────────────────────────────────────┐
│  Top Bar (48px)                                             │
│  [🔄 Sync] [Search...] [✏️ Compose] [⚙️ Settings]          │
├──────────┬─────────────────────┬──────────────────────────┤
│          │                     │                          │
│ Sidebar  │   Email List        │   Reading Pane           │
│ (256px)  │   (384px)           │   (Flex-1)               │
│          │                     │                          │
│ Filters  │   [Urgent Badge]    │   Subject                │
│ - All    │   Subject Line      │   From: ...              │
│ - Unread │   Sender            │   To: ...                │
│ - Urgent │   Snippet...        │   Date: ...              │
│ - Normal │   [Provider] [Time] │                          │
│ - Low    │                     │   Body Content...        │
│          │   [Normal Badge]    │                          │
│ Accounts │   Subject Line      │   [Reply] [Forward]      │
│ ● Gmail  │   Sender            │   [Archive] [Delete]     │
│ ● Outlook│   Snippet...        │                          │
│ ● Instly │                     │                          │
│          │                     │                          │
└──────────┴─────────────────────┴──────────────────────────┘
```

---

## 3. Component Redesigns

### 3.1 Sidebar

**Visual Updates:**
- White background (not dark)
- Light gray hover states
- Blue active selection
- Clean iconography
- Account status indicators

**Structure:**
```
┌─────────────────┐
│ 📧 Email Hub    │ (Logo/Title)
│ 8 inboxes       │ (Subtitle)
├─────────────────┤
│ 📬 All (15)     │ (Filter button)
│ ● Unread (5)   │ (Blue dot for unread)
│ 🚨 Urgent (2)   │ (Red icon)
│ 📋 Normal (8)   │ (Blue icon)
│ 📉 Low (5)      │ (Gray icon)
├─────────────────┤
│ Accounts:       │ (Section header)
│ ● Gmail         │ (Green dot = connected)
│ ● Outlook (3)   │
│ ● Instantly     │
└─────────────────┘
```

### 3.2 Top Bar

**Visual Updates:**
- 48px height (Outlook standard)
- White background with subtle shadow
- Blue primary button (Compose)
- Search bar with icon
- Action buttons with hover states

**Structure:**
```
[🔄] [────── Search emails... ──────] [Compose] [⚙️]
```

### 3.3 Email List

**Visual Updates:**
- Clean white cards with subtle borders
- Hover: light blue background
- Selected: blue left border + light blue bg
- Unread: bold text + blue dot
- Priority badges: colored, rounded
- 2-line preview: subject + snippet
- Metadata row: provider, time, attachments

**Email Card:**
```
┌──────────────────────────────────────────┐
│ [95] ● Payment Failed - Action Required  │ (Unread dot, score, subject)
│ Stripe <billing@stripe.com>              │ (Sender)
│ Your payment method needs updating...    │ (Snippet)
│ GMAIL • 2m ago • 📎                       │ (Provider, time, attachment)
└──────────────────────────────────────────┘
```

### 3.4 Reading Pane

**Visual Updates:**
- Clean header with email metadata
- Action buttons: primary style (blue)
- Well-formatted body with proper typography
- Attachments section (if applicable)
- Thread indicator (if part of conversation)

**Structure:**
```
┌─────────────────────────────────────────────┐
│ [Urgent • 95] Payment Failed - Action Req  │ (Badge + Subject)
├─────────────────────────────────────────────┤
│ From: Stripe <billing@stripe.com>          │
│ To: colton@email.com                        │
│ Date: Jan 30, 2026 1:23 PM                  │
│                                             │
│ [Reply] [Forward] [Archive] [Mark Read]    │ (Action buttons)
├─────────────────────────────────────────────┤
│                                             │
│ Email body content with proper             │
│ typography, spacing, and formatting        │
│                                             │
│ Links styled in blue                       │
│ Important text stands out                  │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 4. Micro-Interactions

### Hover States
- Email list items: Light blue background (#EFF6FF)
- Buttons: Darken primary color by 5%
- Sidebar items: Light gray background (#F3F4F6)

### Focus States
- All interactive elements: Blue outline (3px, 15% opacity)
- Keyboard navigation: Clear focus ring
- Tab order: Logical (sidebar → list → reading pane)

### Transitions
- All state changes: 150ms ease-in-out
- Hover effects: 100ms ease-out
- Background changes: 200ms ease
- Border changes: 150ms ease

### Loading States
- Skeleton screens for email list
- Spinner for sync action
- Smooth fade-in when content loads

### Empty States
- Centered message with icon
- Helpful text ("No emails found")
- Suggestion (e.g., "Try changing filters")

---

## 5. Information Hierarchy

**High Priority (Bold, Dark):**
- Email subject lines
- Unread indicator dots
- Priority scores
- Action buttons

**Medium Priority (Regular, Medium Gray):**
- Sender names
- Email snippets
- Timestamps
- Provider labels

**Low Priority (Light Gray):**
- Metadata (CC, BCC)
- Secondary actions
- Divider lines

---

## 6. Accessibility

- **WCAG AA Contrast:** All text meets 4.5:1 ratio
- **Keyboard Navigation:** Full support (Tab, Arrow keys, Enter, Esc)
- **Focus Indicators:** Visible on all interactive elements
- **Screen Reader:** Semantic HTML, ARIA labels
- **Reduced Motion:** Respect `prefers-reduced-motion`

---

## 7. Responsive Design

- **Desktop (1280px+):** Full 3-column layout
- **Tablet (768-1279px):** Collapsible sidebar, 2-column
- **Mobile (<768px):** Single column, slide-over panels

---

## 8. Performance

- **Lazy Load:** Virtualized email list (only render visible)
- **Optimistic UI:** Instant feedback on actions
- **Debounce:** Search input (300ms)
- **Memoization:** Expensive computations cached

---

## 9. Implementation Priority

### Phase 1: Design System (30 min)
- Update `tailwind.config.ts` with all tokens
- Add custom colors, spacing, shadows
- Configure typography

### Phase 2: Layout & Structure (45 min)
- Redesign `TopBar` component
- Redesign `Sidebar` component
- Update `page.tsx` layout (proper widths, gaps)

### Phase 3: Email List (60 min)
- Redesign `EmailList` component
- Add proper card styling
- Implement hover/selection states
- Add priority badges

### Phase 4: Reading Pane (45 min)
- Redesign `EmailView` component
- Clean header layout
- Action buttons styling
- Body typography

### Phase 5: Polish & Interactions (30 min)
- Add transitions
- Implement focus states
- Test keyboard navigation
- Final visual tweaks

**Total Estimated Time:** 3.5 hours

---

## 10. Success Criteria

✅ Looks professional like Microsoft Outlook  
✅ Clean, generous whitespace  
✅ Clear visual hierarchy  
✅ Smooth interactions and transitions  
✅ Fully keyboard accessible  
✅ Responsive across devices  
✅ Fast and performant  
✅ Delightful to use  

---

**Next:** Implement this plan step-by-step, testing at each phase.
