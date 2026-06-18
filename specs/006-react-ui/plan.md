# Implementation Plan: React UI Refresh (Dark Theme + Tailwind Reuse)

**Branch**: `008-react-ui` | **Date**: 2026-06-18 | **Spec**: `specs/006-react-ui/spec.md`
**Input**: Feature specification from `/specs/006-react-ui/spec.md`

## Summary

Refresh the existing React chat UI with minimal-boilerplate visual improvements: dark blue + amber theme, Tailwind-based styling, top navbar, markdown-rendered streaming output box, animated dots loading state with progress placeholder text, improved desktop space usage, and attachment chips (filename visible) in user messages. Keep code clean by extracting repeated/long Tailwind class strings to a single reusable class-token module.

## Technical Context

**Language/Version**: TypeScript 5.5 + React 18.3.1  
**Primary Dependencies**: React, Vite, socket.io-client, Tailwind CSS, react-markdown  
**Storage**: N/A (browser in-memory state only)  
**Testing**: Vitest + React Testing Library (component behavior), existing lint/typecheck gates  
**Target Platform**: Modern desktop browsers (baseline), responsive support for smaller widths  
**Project Type**: Frontend web application within monorepo  
**Performance Goals**: Streaming token render flush <= 120ms cadence; first visible streamed content <= 500ms from event receipt on local dev baseline  
**Constraints**: Minimal boilerplate, Tailwind-only styling (no UI kit), centralized theme tokens, centralized long class-name reuse file, preserve existing REST + Socket.IO contracts  
**Scale/Scope**: Single-page app with 3 sections (Chat functional; Quiz/Evaluation placeholders), single active chat session per browser tab

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Code Quality Gate: PASS. Enforce `npm run lint`, `npm run build` (typecheck + bundling), and keep UI class reuse in one module to reduce duplication.
- Testing Gate: PASS. Add/maintain unit/component tests for message rendering, attachment chips, loading indicator state, and markdown stream rendering; no regression to existing socket event routing.
- UX Consistency Gate: PASS. Preserve current 3-tab IA (Chat/Quiz/Evaluation), keep accessibility labels and disabled states, and apply consistent dark theme tokens from one source.
- Performance Gate: PASS. Keep batched token strategy and avoid per-token heavy markdown parsing side-effects; validate smooth rendering with local manual perf check.
- Maintainability Gate: PASS. Document token/class extraction strategy in quickstart and keep component responsibilities explicit (new dedicated user-message component).

## Project Structure

### Documentation (this feature)

```text
specs/006-react-ui/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── api-contracts.md
│   └── ui-component-contracts.md
└── tasks.md
```

### Source Code (repository root)

```text
backend_service/
  app/
  tests/

react_ui/
├── src/
│   ├── components/
│   │   ├── Chat/
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── MessageList.tsx
│   │   │   ├── UserMessage.tsx
│   │   │   ├── InputArea.tsx
│   │   │   └── FileUploader.tsx
│   │   ├── Navigation.tsx
│   │   └── Navbar.tsx
│   ├── styles/
│   │   ├── theme.ts
│   │   └── uiClasses.ts
│   ├── hooks/
│   ├── services/
│   ├── schemas.ts
│   ├── App.tsx
│   └── main.tsx
└── tests/
```

**Structure Decision**: Keep current monorepo and extend only `react_ui/` for this feature iteration. No backend API shape changes required.

## Phase 0: Research Focus

- Tailwind minimal setup for existing Vite+React codebase.
- Safe markdown rendering strategy for streamed text.
- Reusable class-token extraction pattern to avoid long inline class strings.
- Lightweight animated loader and placeholder integration pattern.

## Phase 1: Design Outputs

- `data-model.md`: add attachment metadata in chat messages and UI theme/class token entities.
- `contracts/api-contracts.md`: confirm no backend contract changes; clarify rendering behavior constraints.
- `contracts/ui-component-contracts.md`: define component input/output contracts for Navbar, UserMessage, StreamResponseBox.
- `quickstart.md`: include Tailwind setup, theme token location, and class-token reuse guidance.

## Post-Design Constitution Check

- Code Quality Gate: PASS. Design explicitly separates theme tokens and class maps.
- Testing Gate: PASS. Component contracts make tests straightforward and targeted.
- UX Consistency Gate: PASS. Clarified interactive states, loading, markdown display, and attachment visibility.
- Performance Gate: PASS. Continues batched token updates and avoids introducing heavy design-system runtime overhead.
- Maintainability Gate: PASS. New dedicated `UserMessage` component + centralized style tokens reduce churn.

## Complexity Tracking

No constitution violations requiring exceptions.
