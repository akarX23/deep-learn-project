# Implementation Plan: React Web UI for AI Tutor

**Branch**: `008-react-ui` | **Date**: 2026-06-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/006-react-ui/spec.md`

## Summary

A React 18 + TypeScript SPA bootstrapped with Vite that provides a streaming Chat interface for the AI Tutor application. The app connects to the existing Python FastAPI + Socket.IO backend, listens to `stream-tokens-skt` and `clarify-user-level-skt` WebSocket events, and submits user prompts with optional PDF uploads (max 3 files, 20 MB each) to `/api/chat/request` as multipart form data. Two additional sections (Quiz, Evaluation) are scaffolded as placeholders. All backend URLs are environment-variable-driven.

## Technical Context

**Language/Version**: TypeScript 5.x, React 18, Node.js 20 (build toolchain)
**Primary Dependencies**: Vite 5 (build), socket.io-client 4 (WebSocket), React 18 (UI)
**Storage**: N/A — no client-side persistence in this iteration
**Testing**: Vitest + React Testing Library (unit/component tests)
**Target Platform**: Modern desktop browsers (Chrome, Firefox, Safari — latest 2 versions)
**Project Type**: Web application (SPA — single-page application)
**Performance Goals**: First streamed token visible in chat ≤ 500ms after socket event arrival; page TTI ≤ 3s on standard broadband
**Constraints**: PDF uploads only (application/pdf), max 3 files per request, max 20 MB per file; no SSR; no mobile layout required
**Scale/Scope**: Single-user browser session; 3 navigation sections; 1 functional (Chat) + 2 placeholder sections

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Code Quality Gate**: ESLint + Prettier enforced via Vite project scripts. TypeScript strict mode enabled (`"strict": true` in tsconfig). All files must pass `eslint --max-warnings 0` before merge. No `any` types except at explicit schema boundaries (`data: Record<string, any>` in `StreamTokensEventBody`).

- **Testing Gate**: Unit tests required for all custom hooks (`useSocketEvent`, `useBatchedTokens`, `usePdfValidator`) and the `submitChatRequest` service function. Component tests required for `ChatWindow`, `InputArea`, and `FileUploader` using React Testing Library. No regression in existing Python backend tests. Vitest run must pass in CI.

- **UX Consistency Gate**: Interaction patterns mirror the existing Python `ui_frontend` (chat history list with user/assistant roles, streaming token accumulation into assistant bubble, clarification message rendered as info bubble). Pleasant theme, clean layout; no complex animations. Accessible: labels on all form controls, file input described with `aria-label`, submit button disabled state communicated to assistive technology.

- **Performance Gate**: Streaming token render latency ≤ 500ms (debounced flush at 100ms interval). TTI ≤ 3s on standard broadband. Bundle size target: ≤ 500KB gzipped (Vite bundle analysis to be run post-build). Validation: manually timed in Chrome DevTools against local backend.

- **Maintainability Gate**: `src/schemas.ts` is the single source of truth for types mirrored from Python schemas. All env vars documented in `.env.example`. Non-obvious decisions (debounce interval, singleton socket, repeated form keys for array) documented in `research.md`. No dead code or commented-out logic at merge.

## Project Structure

### Documentation (this feature)

```text
specs/006-react-ui/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
react_ui/                      # New top-level directory for the React SPA
  src/
    components/
      Chat/
        ChatWindow.tsx          # Root chat section; composes MessageList + InputArea
        MessageList.tsx         # Renders chat history (user + assistant bubbles)
        InputArea.tsx           # Textarea + send button + file uploader
        FileUploader.tsx        # PDF file picker with validation UI
      Quiz/
        QuizPlaceholder.tsx     # "Coming soon" placeholder
      Evaluation/
        EvaluationPlaceholder.tsx  # "Coming soon" placeholder
      Navigation.tsx            # Tab bar: Chat | Quiz | Evaluation
    hooks/
      useSocketEvent.ts         # Subscribes to a named socket event; cleanup on unmount
      useBatchedTokens.ts       # Buffers streamed tokens in ref, flushes to state @ 100ms
      usePdfValidator.ts        # Validates MIME, count, and size; returns errors + valid files
    services/
      socket.ts                 # Module-level socket.io-client singleton + getSocket()
      api.ts                    # submitChatRequest(FormData) → fetch to /api/chat/request
    schemas.ts                  # TypeScript types mirrored from project/schemas.py + events.py
    config.ts                   # VITE_ env var access with startup validation
    App.tsx                     # Root: section state, event routing, socket initialization
    main.tsx                    # ReactDOM.createRoot entry point
  public/
    index.html
  .env                          # Dev environment variables (not committed)
  .env.example                  # Template with all required VITE_ variables (committed)
  .env.production               # Production env vars (not committed)
  vite.config.ts
  tsconfig.json
  package.json
  README.md
```

**Structure Decision**: Web application (Option 2 variant — frontend only). The React SPA lives in `react_ui/` at the repository root alongside the existing Python agent modules. No backend changes required; the new directory is purely additive.

## Complexity Tracking

*No constitution violations. All gates pass without exceptions.*
