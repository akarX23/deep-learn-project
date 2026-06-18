# Tasks: React UI Streaming-State Refactor

**Input**: Design documents from `/specs/006-react-ui/`  
**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: No explicit test tasks are generated because the current specification does not explicitly request TDD or test-first execution for this iteration.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Ensure baseline dependencies/config support the stream refactor work.

- [X] T001 Verify streaming-related dependencies are declared in `react_ui/package.json`
- [X] T002 Verify Tailwind + PostCSS build pipeline config in `react_ui/tailwind.config.js` and `react_ui/postcss.config.js`
- [X] T003 Verify global stylesheet setup for utility classes in `react_ui/src/index.css` and `react_ui/src/main.tsx`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Align shared types/contracts/components around explicit completion and local stream ownership.

**⚠️ CRITICAL**: No user story work should proceed until this phase is complete.

- [X] T004 Update stream event TypeScript contracts for `done` and `tokens_used` in `react_ui/src/schemas.ts`
- [X] T005 [P] Refine reusable stream/loading style tokens in `react_ui/src/styles/theme.ts` and `react_ui/src/styles/uiClasses.ts`
- [X] T006 [P] Refactor `StreamResponseBox` props/state contract for local stream ownership in `react_ui/src/components/Chat/StreamResponseBox.tsx`
- [X] T007 [P] Refine `LoadingIndicator` display support for stream placeholder/usage context in `react_ui/src/components/Chat/LoadingIndicator.tsx`
- [X] T008 Remove batched token hook usage path from architecture and imports in `react_ui/src/components/Chat/ChatWindow.tsx` and `react_ui/src/hooks/useBatchedTokens.ts`

**Checkpoint**: Shared contracts and stream primitives are ready for user-story implementation.

---

## Phase 3: User Story 1 - Send a Chat Message with PDF Upload (Priority: P1) 🎯 MVP

**Goal**: Deliver direct per-token markdown rendering in `StreamResponseBox` with explicit completion and `tokens_used` display while preserving chat submit/upload flow.

**Independent Test**: Submit a prompt with optional PDFs and observe immediate token-by-token markdown updates in `StreamResponseBox`, completion only on `done: true`, and `tokens_used` shown beneath the response when provided.

- [X] T009 [US1] Implement local `stream-tokens-skt` subscription/handling inside `react_ui/src/components/Chat/StreamResponseBox.tsx`
- [X] T010 [US1] Implement explicit completion logic (`data.done === true`) in `react_ui/src/components/Chat/StreamResponseBox.tsx`
- [X] T011 [US1] Render `tokens_used` below each streamed response box in `react_ui/src/components/Chat/StreamResponseBox.tsx`
- [X] T012 [US1] Keep progress placeholder behavior inside `react_ui/src/components/Chat/StreamResponseBox.tsx`
- [X] T013 [US1] Refactor `MessageList` to pass stable message identity/sid into stream boxes in `react_ui/src/components/Chat/MessageList.tsx`
- [X] T014 [US1] Refactor `ChatWindow` to manage message list structure only (no streamed token content updates) in `react_ui/src/components/Chat/ChatWindow.tsx`
- [X] T015 [US1] Remove timer-driven stream completion path in `react_ui/src/components/Chat/ChatWindow.tsx`
- [X] T016 [US1] Preserve user attachment chip rendering in `react_ui/src/components/Chat/UserMessage.tsx` and `react_ui/src/components/Chat/MessageList.tsx`
- [X] T017 [US1] Keep multipart submit + sid wiring stable during stream refactor in `react_ui/src/components/Chat/ChatWindow.tsx` and `react_ui/src/services/api.ts`

**Checkpoint**: US1 is independently demoable with explicit done-driven stream completion and tokens-used rendering.

---

## Phase 4: User Story 2 - Receive User Level Clarification Prompt (Priority: P2)

**Goal**: Keep clarification behavior correct while stream handling shifts fully into `StreamResponseBox`.

**Independent Test**: Simulate `clarify-user-level-skt` and verify info bubble rendering remains intact while non-teaching stream packets remain ignored.

- [X] T018 [US2] Preserve clarification event insertion behavior in `react_ui/src/components/Chat/ChatWindow.tsx`
- [X] T019 [US2] Ensure non-teaching stream packets are ignored in `react_ui/src/components/Chat/StreamResponseBox.tsx`
- [X] T020 [US2] Keep clarification/info visual presentation consistent in `react_ui/src/components/Chat/MessageList.tsx`

**Checkpoint**: US2 remains independently verifiable with mocked socket events.

---

## Phase 5: User Story 3 - Scaffold Navigation for Future Sections (Priority: P3)

**Goal**: Preserve polished app shell/navigation while stream architecture changes are introduced.

**Independent Test**: Navbar and section switching continue to work with no regressions in Quiz/Evaluation placeholders.

- [X] T021 [US3] Verify navbar integration remains stable with refactored chat section in `react_ui/src/App.tsx` and `react_ui/src/components/Navbar.tsx`
- [X] T022 [US3] Verify section navigation behavior/style integrity in `react_ui/src/components/Navigation.tsx`
- [X] T023 [US3] Verify placeholder section rendering remains intact in `react_ui/src/components/Quiz/QuizPlaceholder.tsx` and `react_ui/src/components/Evaluation/EvaluationPlaceholder.tsx`

**Checkpoint**: US3 shell behavior is independently intact.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Sync docs/contracts and run final quality validation.

- [X] T024 [P] Sync stream completion and tokens-used semantics in `specs/006-react-ui/contracts/api-contracts.md`
- [X] T025 [P] Sync `StreamResponseBox` ownership contract and props in `specs/006-react-ui/contracts/ui-component-contracts.md`
- [X] T026 [P] Sync verification steps for explicit `done` completion in `specs/006-react-ui/quickstart.md`
- [X] T027 Validate accessibility of loading/secondary usage text in `react_ui/src/components/Chat/StreamResponseBox.tsx` and `react_ui/src/components/Chat/LoadingIndicator.tsx`
- [ ] T028 Run local quality gates from `react_ui/package.json` scripts and resolve issues across `react_ui/src/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Starts immediately.
- **Phase 2 (Foundational)**: Depends on Phase 1 and blocks all user stories.
- **Phase 3 (US1)**: Depends on Phase 2 and defines MVP.
- **Phase 4 (US2)**: Depends on Phase 2 and extends chat behavior correctness.
- **Phase 5 (US3)**: Depends on Phase 2 and can proceed in parallel with US2.
- **Phase 6 (Polish)**: Depends on completion of desired user stories.

### User Story Dependencies

- **US1 (P1)**: No dependency on other stories after Foundational phase.
- **US2 (P2)**: Depends on chat orchestration from US1 but remains independently verifiable.
- **US3 (P3)**: Independent from streaming internals; depends only on app shell.

### Within Each User Story

- Establish component/state ownership before final UI wiring.
- Complete stream completion and usage-display logic before removing old paths.
- Preserve API/socket integration contracts during refactor.

---

## Parallel Opportunities

- Foundational: `T005`, `T006`, and `T007` can run in parallel after `T004`.
- US1: `T009` and `T016` can run in parallel; `T013` and `T015` can run in parallel once stream contract is stable.
- US3: `T021`, `T022`, and `T023` can run in parallel.
- Polish: `T024`, `T025`, and `T026` can run in parallel.

---

## Parallel Example: User Story 1

```bash
Task T009: react_ui/src/components/Chat/StreamResponseBox.tsx
Task T016: react_ui/src/components/Chat/UserMessage.tsx
Task T013: react_ui/src/components/Chat/MessageList.tsx
Task T015: react_ui/src/components/Chat/ChatWindow.tsx
```

---

## Parallel Example: User Story 3

```bash
Task T021: react_ui/src/App.tsx and react_ui/src/components/Navbar.tsx
Task T022: react_ui/src/components/Navigation.tsx
Task T023: react_ui/src/components/Quiz/QuizPlaceholder.tsx and react_ui/src/components/Evaluation/EvaluationPlaceholder.tsx
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 (US1).
3. Validate explicit `done` completion and `tokens_used` rendering.
4. Demo/ship MVP.

### Incremental Delivery

1. Foundation complete (Phases 1-2).
2. Deliver US1 stream refactor.
3. Validate and deliver US2 clarification integrity.
4. Validate and deliver US3 shell stability.
5. Execute Phase 6 validation/docs sync.

### Parallel Team Strategy

1. Engineer A: Stream internals (`StreamResponseBox`, `LoadingIndicator`, contracts).
2. Engineer B: Chat orchestration/messages (`ChatWindow`, `MessageList`, `UserMessage`).
3. Engineer C: Shell and docs sync (`App`, `Navigation`, placeholders, quickstart/contracts).

---

## Notes

- `[P]` marks file-isolated tasks suitable for parallel execution.
- Story labels appear only on user-story phases.
- Each user story includes independent validation criteria.
- Keep implementation minimal while enforcing explicit completion semantics.
