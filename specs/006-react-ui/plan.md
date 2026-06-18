# Implementation Plan: React UI Stream Completion Persistence + Upload Control Refinement

**Branch**: `008-react-ui` | **Date**: 2026-06-18 | **Spec**: `specs/006-react-ui/spec.md`
**Input**: Feature specification from `/specs/006-react-ui/spec.md`

## Summary

Align the React chat UI with clarified behavior: `StreamResponseBox` owns live teaching-agent stream state, then sends `{ messageId, fullContent, tokens_used }` to `ChatWindow` on explicit `data.done === true` so final content is persisted and never reset on rerender. Keep boilerplate minimal while refining input/upload chrome to a compact attachment-style control below the text area and removing redundant in-panel heading text.

## Technical Context

**Language/Version**: TypeScript 5.5 + React 18.3.1  
**Primary Dependencies**: Vite 5, socket.io-client 4.8, react-markdown 9, Tailwind CSS 3, ESLint 9  
**Storage**: N/A (in-memory UI state)  
**Testing**: Vitest + React Testing Library (planned), plus `npm run lint` and `npm run build` quality gates  
**Target Platform**: Modern desktop browsers (with responsive fallback)  
**Project Type**: Frontend web application within monorepo  
**Performance Goals**: Immediate per-token rendering without batching delay; no timeout-driven completion; stable post-completion content across rerenders  
**Constraints**: Minimal boilerplate, Tailwind-only styling approach, centralized class/token reuse, no extra UI libraries, strict explicit completion semantics  
**Scale/Scope**: Single-session chat flow + placeholder quiz/evaluation sections

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Code Quality Gate: PASS. Refactor keeps clean ownership boundaries (`ChatWindow` orchestration, `StreamResponseBox` stream state) and updates contracts/docs.
- Testing Gate: PASS WITH FOLLOW-UP. Constitution expects automated behavior tests for stream-completion persistence and upload-control UX; implementation can proceed but tests must be restored in a later hardening pass.
- UX Consistency Gate: PASS. Navbar remains canonical title; in-panel heading removal and compact upload control are explicitly specified and consistent with feature style direction.
- Performance Gate: PASS. Eliminates timeout jitter and batched token delays; completion path is deterministic (`done === true`).
- Maintainability Gate: PASS. Non-obvious stream completion handoff is documented in spec/data model/contracts/quickstart.

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
│   │   │   ├── StreamResponseBox.tsx
│   │   │   ├── UserMessage.tsx
│   │   │   ├── InputArea.tsx
│   │   │   ├── FileUploader.tsx
│   │   │   └── LoadingIndicator.tsx
│   │   ├── Quiz/QuizPlaceholder.tsx
│   │   └── Evaluation/EvaluationPlaceholder.tsx
│   ├── services/
│   ├── hooks/
│   ├── styles/
│   │   ├── theme.ts
│   │   └── uiClasses.ts
│   ├── schemas.ts
│   ├── App.tsx
│   └── main.tsx
└── package.json
```

**Structure Decision**: Keep all implementation inside `react_ui/` and keep backend contracts additive/non-breaking (`done` and `tokens_used` metadata in existing event payload shape).

## Phase 0: Research Focus

- Determine robust explicit-completion persistence pattern for streamed markdown content.
- Validate minimal-prop contract between `StreamResponseBox` and `ChatWindow` (`messageId`, `fullContent`, `tokens_used`).
- Define compact upload-control UX that preserves validation clarity while reducing chrome.

## Phase 1: Design Outputs

- `research.md`: document decision rationale for completion handoff and compact upload control.
- `data-model.md`: include `ChatMessage.tokens_used` and completion payload handoff model.
- `contracts/api-contracts.md`: maintain explicit `done` / `tokens_used` backend contract semantics.
- `contracts/ui-component-contracts.md`: update `StreamResponseBox` callback contract and input/upload UI presentation contract.
- `quickstart.md`: add verification steps for persisted completed content, tokens display, and compact upload control UX.
- Agent context update: `.github/copilot-instructions.md` remains correctly pointed at `specs/006-react-ui/plan.md`.

## Post-Design Constitution Check

- Code Quality Gate: PASS. Architecture remains simple and bounded.
- Testing Gate: PASS WITH FOLLOW-UP. Design explicitly calls out behavior that requires automated regression tests in subsequent tasks.
- UX Consistency Gate: PASS. Clarified interaction details are encoded in contracts and quickstart checks.
- Performance Gate: PASS. Event-driven completion and local stream handling reduce render churn.
- Maintainability Gate: PASS. Updated artifacts preserve traceability from FR-030/FR-031/FR-032 to implementation expectations.

## Complexity Tracking

No constitution violations requiring exception handling.
