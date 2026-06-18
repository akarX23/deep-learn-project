# Quickstart: React UI Refresh (Feature 006)

**Feature**: `specs/006-react-ui` | **Branch**: `008-react-ui`

## Prerequisites

- Node.js 20+
- npm 10+
- Backend running at `http://localhost:8000`

## 1. Install Dependencies

```bash
cd react_ui
npm install
npm install -D tailwindcss postcss autoprefixer
npm install react-markdown
```

## 2. Initialize Tailwind (Minimal Setup)

```bash
npx tailwindcss init -p
```

Configure `tailwind.config.*` content paths for `index.html` and `src/**/*.{ts,tsx}`.

In `src/index.css`, include:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

## 3. Configure Environment Variables

```bash
cp .env.example .env
```

Set:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=http://localhost:8000
```

## 4. Add Reusable UI Style Files

Create and use:
- `src/styles/theme.ts` (all color tokens)
- `src/styles/uiClasses.ts` (long/repeated Tailwind class strings)

Rule: avoid hardcoding repeated long class lists in component JSX.

## 5. Run Locally

```bash
npm run dev
```

## 6. Verify Key UX Behaviors

- Navbar with title is visible.
- No redundant in-panel "Ask AI Tutor" heading is shown in chat content area.
- Dark blue + amber theme is applied consistently.
- Chat container uses more desktop width without readability loss.
- Streamed assistant output renders markdown in dedicated box.
- Animated dots loader appears with progress placeholder text while waiting/streaming.
- Stream completion occurs only when a payload with `data.done === true` is received.
- When completion payload includes `data.tokens_used`, the value appears below the related stream response box.
- On completion, assistant content remains stable after rerender because chat state persists `{ messageId, fullContent, tokens_used }` from stream completion callback.
- Upload control appears below text area as a compact attachment-style trigger (icon + `Upload`) with nearby limit helper text.
- Submitted user messages show attachment chips with filename.
- Non-teaching-agent stream events remain ignored.

## 7. Quality Gates

```bash
npm run lint
npm run build
npm run test
```

## 8. Notes for Minimal Boilerplate

- Prefer utility composition over new abstractions unless reuse is clear.
- Keep new component count minimal: `Navbar`, `UserMessage`, optional `StreamResponseBox`.
- Keep stream event handling isolated in `StreamResponseBox`; avoid parent-level token accumulation state.
- Do not use timeout-based stream completion for teaching-agent packets.
- Persist finalized completion payload in `ChatWindow` message state to prevent content reset on rerenders.
