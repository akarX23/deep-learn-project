# Implementation Plan: React UI Streaming-State Refactor

**Branch**: `008-react-ui` | **Date**: 2026-06-18 | **Spec**: `specs/006-react-ui/spec.md`
**Input**: Feature specification from `/specs/006-react-ui/spec.md`

## Summary

Refine the React UI architecture to maximize streaming responsiveness by moving teaching-agent stream state ownership into `StreamResponseBox`, removing batched token buffering, and using explicit backend completion (`data.done === true`) with `tokens_used` rendering beneath each streamed response. Keep minimal boilerplate, Tailwind-based dark theme, and reusable class-token organization.

## Technical Context

**Language/Version**: TypeScript 5.5 + React 18.3.1  
**Primary Dependencies**: React, Vite, socket.io-client, Tailwind CSS, react-markdown  
**Storage**: N/A (in-memory UI state only)  
**Testing**: Vitest + React Testing Library for component behavior; lint/build for static quality gates  
**Target Platform**: Modern desktop browsers, responsive fallback for smaller viewports  
**Project Type**: Frontend web application within monorepo  
**Performance Goals**: Immediate per-token UI updates without batching delays; completion tied to explicit `done` payload, not timers  
**Constraints**: Minimal boilerplate, no additional UI libraries, centralized theme/class tokens, no timeout-driven stream completion  
**Scale/Scope**: Single-session chat UI with three sections; chat is functional while quiz/evaluation remain placeholders

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Code Quality Gate: PASS. Keep modular component ownership (`ChatWindow` structure vs `StreamResponseBox` stream state) and maintain lint/build compatibility.
- Testing Gate: PASS WITH NOTE. Behavioral changes imply required automated coverage at implementation time (stream completion, tokens_used rendering, no batching).
- UX Consistency Gate: PASS. Existing navigation, accessibility labels, and visual language remain; streaming feedback becomes more direct.
- Performance Gate: PASS. Removing buffered token flushes and timeout completion aligns with responsiveness goals.
- Maintainability Gate: PASS. Contracted ownership boundaries reduce cross-component state churn and simplify reasoning.

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
react_ui/
├── src/
│   ├── components/
│   │   ├── Navbar.tsx
│   │   ├── Navigation.tsx
│   │   ├── Chat/
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── MessageList.tsx
│   │   │   ├── UserMessage.tsx
│   │   │   ├── StreamResponseBox.tsx
│   │   │   ├── LoadingIndicator.tsx
│   │   │   ├── InputArea.tsx
│   │   │   └── FileUploader.tsx
│   │   ├── Quiz/QuizPlaceholder.tsx
│   │   └── Evaluation/EvaluationPlaceholder.tsx
│   ├── styles/
│   │   ├── theme.ts
│   │   └── uiClasses.ts
│   ├── hooks/
│   ├── services/
│   ├── schemas.ts
│   ├── App.tsx
│   └── main.tsx
└── package.json
```

**Structure Decision**: Keep all frontend implementation changes inside `react_ui/`; backend event contract remains backward-compatible and additive (`done`, `tokens_used` in `data`).

## Phase 0: Research Focus

- Event-driven stream completion via explicit payload metadata instead of timer heuristics.
- Component-local high-frequency stream rendering to minimize parent re-renders.
- Stable mapping between streamed assistant messages and stream state in `StreamResponseBox`.

## Phase 1: Design Outputs

- `research.md`: capture rationale for removing `useBatchedTokens` and stream ownership refactor.
- `data-model.md`: incorporate completion metadata (`done`, `tokens_used`) and per-response stream state ownership.
- `contracts/api-contracts.md`: codify explicit completion payload semantics.
- `contracts/ui-component-contracts.md`: define `StreamResponseBox` ownership boundaries and `tokens_used` display rule.
- `quickstart.md`: include verification checklist for explicit completion and tokens-used rendering.

## Post-Design Constitution Check

- Code Quality Gate: PASS. Ownership boundaries are explicit and reduce mutable shared state.
- Testing Gate: PASS WITH NOTE. Implementation must include regression tests for explicit `done` completion and `tokens_used` rendering.
- UX Consistency Gate: PASS. Chat remains consistent while improving responsiveness and completion correctness.
- Performance Gate: PASS. Direct stream updates avoid batching delay and timeout jitter.
- Maintainability Gate: PASS. Stream concerns are isolated in one component with clear contract.

## Complexity Tracking

No constitution violations requiring exception handling.
