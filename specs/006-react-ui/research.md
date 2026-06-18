# Research: React Web UI for AI Tutor

**Phase**: Phase 0 — Technology Research
**Feature**: `specs/006-react-ui`
**Branch**: `008-react-ui`
**Date**: 2026-06-18

## Summary

All unknowns from Technical Context resolved. No `NEEDS CLARIFICATION` markers remain.

---

## 1. Socket.IO Client Integration in React 18

**Decision**: Module-level singleton (`src/services/socket.ts`) + `useSocketEvent` custom hook for per-event subscription management.

**Rationale**: A Socket.IO connection is stateful and should be shared across the entire app — one connection per browser session, not one per component mount. Module-level initialization prevents duplicate connections. A `useEffect`-based hook with cleanup (`socket.off`) prevents memory leaks on component unmounts.

**Alternatives considered**:
- Naive per-hook `io()` call: Creates multiple connections on remounts, causes churn.
- React Context only: Works, but initialization timing is harder to control; module singleton is simpler.

---

## 2. Streaming Token Accumulation

**Decision**: `useRef` text buffer + debounced `useState` flush every ~100ms (not per-token state mutation).

**Rationale**: Calling `setState` on every WebSocket token causes one React re-render per token, which at high token rates degrades UI performance. Accumulating tokens in a ref and flushing to state on a timer decouples socket event rate from React render rate while keeping visual feedback responsive.

**Alternatives considered**:
- `useState` per token: O(n) re-renders per message, causes jank.
- `useReducer` with dispatch: Structurally heavier without additional benefit for this single-value accumulation.

---

## 3. Multipart Form Data Submission

**Decision**: Native `FormData` API + `fetch`, with `user_level` submitted as repeated form keys. No `Content-Type` header set explicitly (browser sets it with boundary automatically).

**Rationale**: FastAPI `Form(user_level: list[str])` expects standard repeated form keys. Setting `Content-Type` manually breaks multipart boundary. Native `fetch` + `FormData` requires zero additional dependencies.

**Alternatives considered**:
- `axios` with FormData: Adds a dependency; `fetch` is built-in and sufficient.
- JSON stringify for `user_level`: Breaks FastAPI form parsing expectations.

---

## 4. Environment Variables in Vite

**Decision**: All runtime configuration exposed via `VITE_`-prefixed variables in `.env` / `.env.production`, accessed via `import.meta.env.VITE_*`. Validated at startup in `src/config.ts`.

**Rationale**: Vite only exposes `VITE_`-prefixed vars to the client bundle by design (security boundary). Variables are inlined at build time. Startup validation catches misconfiguration before any UI renders.

**Variables defined**:
- `VITE_API_BASE_URL` — FastAPI backend base URL (e.g., `http://localhost:8000`)
- `VITE_WS_URL` — Socket.IO server URL (e.g., `http://localhost:8000`)

**Alternatives considered**:
- No prefix: Not exposed by Vite build pipeline.
- Runtime config endpoint: Adds a round-trip; overkill for a static SPA.

---

## 5. PDF File Validation (Browser-Side)

**Decision**: Custom `usePdfValidator` hook that synchronously checks MIME type (`application/pdf`), total count (≤ 3), and individual file size (≤ 20 MB) in the `onChange` handler — before any network call.

**Rationale**: Synchronous browser-side validation provides instant feedback. All three validations run in O(n) time with no async operations. Prevents unnecessary backend load for obviously invalid inputs.

**Alternatives considered**:
- Backend-only validation: Poor UX (upload wait, then error); wastes bandwidth.
- Validation library (zod + react-hook-form): Three checks do not justify the dependency.

---

## 6. SPA Structure — No Routing Library

**Decision**: Flat `src/` structure with `currentSection` state string in `App.tsx`. Three sections: Chat (functional), Quiz (placeholder), Evaluation (placeholder). No React Router.

**Rationale**: Tab-based state (`useState`) is sufficient for navigation without URL-driven routing. Eliminates a dependency. Easy to replace with React Router later if deep-linking is required.

**Alternatives considered**:
- React Router: Useful when you need URL-driven navigation; not needed here.
- Zustand or Redux: State is a single string; `useState` is sufficient.

**Source layout**:
```
react_ui/
  src/
    components/
      Chat/            # ChatWindow, MessageList, InputArea, FileUploader
      Quiz/            # QuizPlaceholder
      Evaluation/      # EvaluationPlaceholder
      Navigation.tsx
    hooks/             # useSocketEvent, useBatchedTokens, usePdfValidator
    services/          # socket.ts (singleton), api.ts (fetch wrapper)
    schemas.ts         # Mirrored TypeScript types from Python schemas
    config.ts          # Env var access + startup validation
    App.tsx
    main.tsx
  public/
  .env
  .env.production
  vite.config.ts
  tsconfig.json
  package.json
```

---

## 7. TypeScript Schema Types

**Decision**: Single `src/schemas.ts` file with TypeScript `interface` for data shapes and a `const` object (not `enum`) for WebSocket event names.

**Rationale**: A single authoritative schema file prevents drift between component-level type definitions. `interface` over `type` for extensibility. `const` object over `enum` for event names is more ergonomic at runtime (`WebSocketEvents.STREAM_TOKENS_SKT === 'stream-tokens-skt'` without special enum semantics).

**Types to define**:
- `StreamTokensEventBody` — mirrors `project/schemas.py::StreamTokensEventBody`
- `ClarifyUserLevelEvent` — mirrors `project/schemas.py::ClarifyUserLevelEvent`
- `WebSocketEvents` const — mirrors `project/events.py::WebSocketEvents` enum values
- `ChatMessage` — local UI entity (not in Python schemas)
- `UserRequest` — mirrors `project/schemas.py::UserRequest`

**Alternatives considered**:
- Auto-generated from OpenAPI: Would require tooling setup; manual types are minimal.
- TypeScript `enum`: Less ergonomic for runtime string comparisons; `const` is preferred.
