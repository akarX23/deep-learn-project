# Tasks: React UI Stream Completion Persistence + Upload Control Refinement

**Input**: Design documents from `/specs/006-react-ui/`  
**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: No explicit test tasks are generated because the current specification does not explicitly request test-first/TDD execution for this iteration.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm baseline frontend setup supports the clarified stream-persistence and compact-upload changes.

- [X] T001 Verify stream-related dependencies and scripts in `react_ui/package.json`
- [X] T002 Verify Tailwind + PostCSS configuration in `react_ui/tailwind.config.js` and `react_ui/postcss.config.js`
- [X] T003 Verify shared stylesheet wiring in `react_ui/src/index.css` and `react_ui/src/main.tsx`
- [X] T004 Verify environment variable contract placeholders in `react_ui/.env.example` and `react_ui/src/config.ts`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish core schemas, component contracts, and shared styling needed by all user stories.

**⚠️ CRITICAL**: No user story work should begin until this phase is complete.

- [X] T005 Update stream and message schema types (including `ChatMessage.tokens_used`) in `react_ui/src/schemas.ts`
- [X] T006 Define completion payload typing (`messageId`, `fullContent`, `tokens_used`) in `react_ui/src/schemas.ts`
- [X] T007 [P] Refine shared stream/upload style tokens in `react_ui/src/styles/theme.ts` and `react_ui/src/styles/uiClasses.ts`
- [X] T008 [P] Update `StreamResponseBox` prop contract for payload-based `onDone` callback in `react_ui/src/components/Chat/StreamResponseBox.tsx`
- [X] T009 [P] Update `MessageList` contract to pass stable stream identity and callback payload in `react_ui/src/components/Chat/MessageList.tsx`
- [X] T010 Remove deprecated non-owned stream paths from `react_ui/src/components/Chat/ChatWindow.tsx` and `react_ui/src/hooks/useBatchedTokens.ts`

**Checkpoint**: Shared contracts and architecture boundaries are ready for story work.

---

## Phase 3: User Story 1 - Send a Chat Message with PDF Upload (Priority: P1) 🎯 MVP

**Goal**: Deliver stable explicit-completion stream persistence and refined chat input/upload UX while preserving PDF request flow.

**Independent Test**: Submit a prompt with optional PDFs, stream a teaching-agent response, confirm done-only completion, persisted final markdown content (no reset), and `tokens_used` display, using compact upload control below textarea.

- [X] T011 [US1] Implement token accumulation and done-only completion handling inside `react_ui/src/components/Chat/StreamResponseBox.tsx`
- [X] T012 [US1] Emit completion payload `{ messageId, fullContent, tokens_used }` from `react_ui/src/components/Chat/StreamResponseBox.tsx`
- [X] T013 [US1] Persist completion payload into message-list state in `react_ui/src/components/Chat/ChatWindow.tsx`
- [X] T014 [US1] Ensure stream completion updates `isStreaming` and persisted `tokens_used` in `react_ui/src/components/Chat/ChatWindow.tsx`
- [X] T015 [US1] Render finalized usage metadata beneath streamed assistant content in `react_ui/src/components/Chat/StreamResponseBox.tsx` and `react_ui/src/components/Chat/MessageList.tsx`
- [X] T016 [US1] Remove redundant in-panel "Ask AI Tutor" heading from `react_ui/src/components/Chat/ChatWindow.tsx`
- [X] T017 [US1] Refine prompt area to rely on textarea placeholder guidance in `react_ui/src/components/Chat/InputArea.tsx`
- [X] T018 [US1] Implement compact attachment-style upload trigger and helper text below textarea in `react_ui/src/components/Chat/FileUploader.tsx` and `react_ui/src/components/Chat/InputArea.tsx`
- [X] T019 [US1] Preserve PDF validation behavior (type/count/size) in `react_ui/src/hooks/usePdfValidator.ts` and `react_ui/src/components/Chat/FileUploader.tsx`
- [X] T020 [US1] Preserve multipart submit + sid + file wiring in `react_ui/src/services/api.ts` and `react_ui/src/components/Chat/ChatWindow.tsx`
- [X] T021 [US1] Preserve submitted attachment chip rendering in `react_ui/src/components/Chat/UserMessage.tsx` and `react_ui/src/components/Chat/MessageList.tsx`

**Checkpoint**: US1 is independently demoable and satisfies completion-persistence + compact-upload requirements.

---

## Phase 4: User Story 2 - Receive User Level Clarification Prompt (Priority: P2)

**Goal**: Keep clarification behavior correct with new stream completion payload persistence.

**Independent Test**: Simulate `clarify-user-level-skt` and non-teaching `stream-tokens-skt`; clarification messages render properly and non-teaching stream packets remain ignored.

- [X] T022 [US2] Preserve clarification event insertion into chat history in `react_ui/src/components/Chat/ChatWindow.tsx`
- [X] T023 [US2] Ensure non-teaching stream packets are ignored in `react_ui/src/components/Chat/StreamResponseBox.tsx`
- [X] T024 [US2] Maintain clarification/info message styling consistency in `react_ui/src/components/Chat/MessageList.tsx` and `react_ui/src/styles/uiClasses.ts`

**Checkpoint**: US2 remains independently verifiable with mocked socket payloads.

---

## Phase 5: User Story 3 - Scaffold Navigation for Future Sections (Priority: P3)

**Goal**: Preserve polished app shell and placeholder navigation behavior after chat refactor updates.

**Independent Test**: Navbar remains visible, section switching works, and Quiz/Evaluation placeholders remain stable.

- [X] T025 [US3] Verify navbar and chat-shell integration in `react_ui/src/App.tsx` and `react_ui/src/components/Navbar.tsx`
- [X] T026 [US3] Verify section navigation behavior remains intact in `react_ui/src/components/Navigation.tsx`
- [X] T027 [US3] Verify placeholder rendering continuity in `react_ui/src/components/Quiz/QuizPlaceholder.tsx` and `react_ui/src/components/Evaluation/EvaluationPlaceholder.tsx`

**Checkpoint**: US3 shell and placeholder behavior is independently intact.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Keep docs/contracts synchronized and complete non-test validation gates.

- [X] T028 [P] Sync completion persistence semantics in `specs/006-react-ui/contracts/api-contracts.md`
- [X] T029 [P] Sync UI component callback and compact-upload contract details in `specs/006-react-ui/contracts/ui-component-contracts.md`
- [X] T030 [P] Sync data model for `ChatMessage.tokens_used` and completion payload in `specs/006-react-ui/data-model.md`
- [X] T031 [P] Sync manual verification flow in `specs/006-react-ui/quickstart.md`
- [X] T032 Validate loading/status accessibility semantics in `react_ui/src/components/Chat/LoadingIndicator.tsx` and `react_ui/src/components/Chat/StreamResponseBox.tsx`
- [ ] T033 Run non-test quality gates and resolve issues in `react_ui/` via `npm run lint` and `npm run build`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Starts immediately.
- **Phase 2 (Foundational)**: Depends on Phase 1 and blocks all user stories.
- **Phase 3 (US1)**: Depends on Phase 2 and defines MVP delivery.
- **Phase 4 (US2)**: Depends on Phase 2 and extends chat correctness.
- **Phase 5 (US3)**: Depends on Phase 2 and can run in parallel with US2.
- **Phase 6 (Polish)**: Depends on completion of desired user stories.

### User Story Dependencies

- **US1 (P1)**: No dependency on other stories after Foundational phase.
- **US2 (P2)**: Depends on US1 stream/message orchestration surfaces but remains independently testable.
- **US3 (P3)**: Depends on shared app shell only; independent of stream internals.

### Within Each User Story

- Establish schema and callback contracts before UI wiring.
- Complete explicit completion + persistence path before removing old stream paths.
- Preserve request and validation behavior while applying visual refinements.

---

## Parallel Opportunities

- Foundational: `T007`, `T008`, and `T009` can run in parallel after `T005` and `T006`.
- US1: `T016`, `T017`, and `T021` can run in parallel once completion payload contract is stable.
- US3: `T025`, `T026`, and `T027` can run in parallel.
- Polish: `T028`, `T029`, `T030`, and `T031` can run in parallel.

---

## Parallel Example: User Story 1

```bash
Task T016: react_ui/src/components/Chat/ChatWindow.tsx
Task T017: react_ui/src/components/Chat/InputArea.tsx
Task T021: react_ui/src/components/Chat/UserMessage.tsx and react_ui/src/components/Chat/MessageList.tsx
```

---

## Parallel Example: User Story 3

```bash
Task T025: react_ui/src/App.tsx and react_ui/src/components/Navbar.tsx
Task T026: react_ui/src/components/Navigation.tsx
Task T027: react_ui/src/components/Quiz/QuizPlaceholder.tsx and react_ui/src/components/Evaluation/EvaluationPlaceholder.tsx
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup).
2. Complete Phase 2 (Foundational).
3. Complete Phase 3 (US1).
4. Validate done-only completion, payload persistence, and compact upload control behavior.
5. Demo/ship MVP.

### Incremental Delivery

1. Setup + Foundational complete.
2. Deliver US1 and validate independently.
3. Deliver US2 and validate independently.
4. Deliver US3 and validate independently.
5. Complete Phase 6 docs sync and quality gates.

### Parallel Team Strategy

1. Engineer A: Stream and callback contracts (`StreamResponseBox`, `MessageList`, `schemas`).
2. Engineer B: Chat orchestration and input/upload UX (`ChatWindow`, `InputArea`, `FileUploader`).
3. Engineer C: Shell and docs sync (`App`, `Navigation`, placeholders, contracts, quickstart).

---

## Notes

- `[P]` marks file-isolated tasks suitable for parallel execution.
- Story labels are applied only to user story phases.
- Each user story has independent validation criteria.
- Keep boilerplate minimal and avoid adding features outside current spec scope.
