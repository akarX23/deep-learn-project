# Quickstart: React Web UI for AI Tutor

**Feature**: `specs/006-react-ui` | **Branch**: `008-react-ui`

## Prerequisites

- Node.js 20+ (`node --version`)
- npm 10+ or pnpm 9+
- Running AI Tutor backend stack (FastAPI + Socket.IO on `http://localhost:8000`)

---

## 1. Create the React Project

```bash
# From the repository root
npm create vite@latest react_ui -- --template react-ts
cd react_ui
npm install
```

## 2. Install Runtime Dependencies

```bash
npm install socket.io-client
```

## 3. Configure Environment Variables

```bash
# react_ui/.env (development — not committed)
cp .env.example .env
```

Edit `.env`:
```
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=http://localhost:8000
```

## 4. Run the Development Server

```bash
# From react_ui/
npm run dev
```

Opens at `http://localhost:5173` by default.

## 5. Run Tests

```bash
npm run test
```

Runs all Vitest unit and component tests.

## 6. Build for Production

```bash
npm run build
```

Output in `react_ui/dist/`. Check bundle size with:

```bash
npm run build -- --report
```

## 7. Performance Validation Notes

- Budget target: first streamed token visible in chat within 500ms of socket event arrival.
- Budget target: page interactive in under 3s on standard broadband.
- Validation approach:
  - Open Chrome DevTools Performance panel and record from page load.
  - Send one chat request with a short prompt and no files.
  - Confirm token rendering starts quickly and interaction remains smooth.
  - Record observations in sprint notes when implementing.

## 8. End-to-End Verification Checklist

- Start backend and frontend locally.
- Verify app shows three sections: Chat, Quiz, Evaluation.
- Verify Quiz and Evaluation render placeholder content.
- Verify Chat accepts prompt text and submits to `/api/chat/request`.
- Verify PDF validation blocks non-PDF files.
- Verify PDF validation blocks files larger than 20 MB.
- Verify PDF validation blocks adding more than 3 files.
- Verify `stream-tokens-skt` events from `teaching-agent` append to assistant response.
- Verify `stream-tokens-skt` events from other services are ignored.
- Verify `clarify-user-level-skt` events show clarification info in chat.
- Verify submit button is disabled while a response is streaming.

---

## Environment Variables Reference

See [contracts/api-contracts.md](contracts/api-contracts.md) for the full variable list.

| Variable | Description |
|---|---|
| `VITE_API_BASE_URL` | FastAPI backend base URL |
| `VITE_WS_URL` | Socket.IO server URL |

---

## Project Structure Quick Reference

```
react_ui/src/
  App.tsx              # Root — section navigation + socket initialization
  schemas.ts           # TypeScript types mirrored from Python schemas
  config.ts            # Env var access with startup validation
  components/Chat/     # Chat section components
  components/Quiz/     # Placeholder
  components/Evaluation/ # Placeholder
  hooks/               # useSocketEvent, useBatchedTokens, usePdfValidator
  services/            # socket.ts (singleton), api.ts (fetch wrapper)
```

---

## Backend Integration Notes

- The `sid` sent with REST requests is `socket.id` — captured on Socket.IO connection.
- `user_level` defaults to `[]` in this iteration; the backend planner will emit `clarify-user-level-skt` to ask for it.
- File validation (PDF, max 3, max 20 MB) happens entirely in the browser before any upload.
- `stream-tokens-skt` events from services other than `"teaching-agent"` are silently ignored.
