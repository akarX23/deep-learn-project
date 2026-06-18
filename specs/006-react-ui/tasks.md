# Tasks: React Web UI for AI Tutor

**Input**: Design documents from `/specs/006-react-ui/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Test tasks are included for each user story because behavior changes are user-facing and contract-sensitive.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Every task includes an exact file path

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the React workspace and baseline tooling.

- [X] T001 Initialize React + TypeScript Vite app in react_ui/package.json
- [X] T002 Configure TypeScript compiler options in react_ui/tsconfig.json
- [X] T003 [P] Configure Vite build/dev settings in react_ui/vite.config.ts
- [X] T004 [P] Add lint/format scripts and config references in react_ui/package.json
- [X] T005 [P] Define required environment variable template in react_ui/.env.example
- [X] T006 Create source directory skeleton and entry files in react_ui/src/main.tsx

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build shared contracts and infrastructure required by all stories.

**⚠️ CRITICAL**: No user story implementation begins until this phase is complete.

- [X] T007 Define mirrored TypeScript backend contracts in react_ui/src/schemas.ts
- [X] T008 Implement runtime env validation and config exports in react_ui/src/config.ts
- [X] T009 Implement Socket.IO singleton connection service in react_ui/src/services/socket.ts
- [X] T010 [P] Implement reusable socket event subscription hook in react_ui/src/hooks/useSocketEvent.ts
- [X] T011 [P] Implement multipart chat request API client in react_ui/src/services/api.ts
- [X] T012 Create root app shell with section state and socket lifecycle wiring in react_ui/src/App.tsx

**Checkpoint**: Foundation ready; user stories can proceed.

---

## Phase 3: User Story 1 - Send a Chat Message with PDF Upload (Priority: P1) 🎯 MVP

**Goal**: Deliver end-to-end chat request submission with PDF validation and streaming token rendering from `teaching-agent`.

**Independent Test**: User sends a prompt with 0-3 valid PDFs and sees assistant response stream token-by-token in Chat.

### Tests for User Story 1

- [ ] T013 [P] [US1] Add unit tests for PDF validation rules in react_ui/src/hooks/usePdfValidator.test.ts
- [ ] T014 [P] [US1] Add unit tests for token batching behavior in react_ui/src/hooks/useBatchedTokens.test.ts
- [ ] T015 [P] [US1] Add unit tests for multipart form-data request construction in react_ui/src/services/api.test.ts
- [ ] T016 [P] [US1] Add component test for chat send + streaming render flow in react_ui/src/components/Chat/ChatWindow.test.tsx

### Implementation for User Story 1

- [X] T017 [P] [US1] Implement PDF-only file picker UI with count/size validation messaging in react_ui/src/components/Chat/FileUploader.tsx
- [X] T018 [P] [US1] Implement token buffering hook for efficient streaming UI updates in react_ui/src/hooks/useBatchedTokens.ts
- [X] T019 [P] [US1] Implement chat message list rendering for user and assistant roles in react_ui/src/components/Chat/MessageList.tsx
- [X] T020 [US1] Implement prompt input + submit control with disabled streaming state in react_ui/src/components/Chat/InputArea.tsx
- [X] T021 [US1] Implement Chat container to compose input/files/messages and route `stream-tokens-skt` from `teaching-agent` in react_ui/src/components/Chat/ChatWindow.tsx
- [X] T022 [US1] Mount Chat section in app shell and connect submit flow to `/api/chat/request` in react_ui/src/App.tsx

**Checkpoint**: User Story 1 independently functional and demoable (MVP).

---

## Phase 4: User Story 2 - Receive User Level Clarification Prompt (Priority: P2)

**Goal**: Render planner clarification events in chat and keep non-teaching token streams ignored.

**Independent Test**: Simulate `clarify-user-level-skt` and verify clarification appears in chat; simulate non-teaching token source and verify it is ignored.

### Tests for User Story 2

- [ ] T023 [P] [US2] Add component test for clarification event rendering in chat history in react_ui/src/components/Chat/ChatWindow.clarify.test.tsx
- [ ] T024 [P] [US2] Add unit test for non-teaching token filtering logic in react_ui/src/components/Chat/ChatWindow.filtering.test.tsx

### Implementation for User Story 2

- [X] T025 [US2] Implement `clarify-user-level-skt` event handling and info-bubble insertion in react_ui/src/components/Chat/ChatWindow.tsx
- [X] T026 [US2] Implement explicit ignore path for `stream-tokens-skt` payloads where `from_service` is not `teaching-agent` in react_ui/src/components/Chat/ChatWindow.tsx

**Checkpoint**: User Story 2 independently testable with mocked socket events.

---

## Phase 5: User Story 3 - Scaffold Navigation for Future Sections (Priority: P3)

**Goal**: Provide Chat, Quiz, Evaluation section scaffold with placeholders for non-chat sections.

**Independent Test**: User can switch sections and see placeholders for Quiz/Evaluation without runtime errors.

### Tests for User Story 3

- [ ] T027 [P] [US3] Add component test for section switching and placeholder rendering in react_ui/src/components/Navigation.test.tsx

### Implementation for User Story 3

- [X] T028 [P] [US3] Implement top-level section navigation component in react_ui/src/components/Navigation.tsx
- [X] T029 [P] [US3] Implement Quiz placeholder section component in react_ui/src/components/Quiz/QuizPlaceholder.tsx
- [X] T030 [P] [US3] Implement Evaluation placeholder section component in react_ui/src/components/Evaluation/EvaluationPlaceholder.tsx
- [X] T031 [US3] Wire navigation state to section rendering in app shell in react_ui/src/App.tsx

**Checkpoint**: All three sections render; Chat remains functional, Quiz/Evaluation are scaffolded.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Hardening, documentation, and quality/performance verification.

- [X] T032 [P] Add accessibility labels and keyboard/disabled-state checks for chat controls in react_ui/src/components/Chat/InputArea.tsx
- [X] T033 [P] Add accessibility labels and error announcement support for file validation in react_ui/src/components/Chat/FileUploader.tsx
- [X] T034 Add app usage and environment configuration docs in react_ui/README.md
- [X] T035 Validate performance budget instrumentation notes and outcomes in specs/006-react-ui/quickstart.md
- [X] T036 Run end-to-end local verification steps and capture expected behavior checklist in specs/006-react-ui/quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies.
- **Phase 2 (Foundational)**: Depends on Phase 1; blocks all user stories.
- **Phase 3 (US1)**: Depends on Phase 2; defines MVP.
- **Phase 4 (US2)**: Depends on Phase 2 and extends chat event behavior.
- **Phase 5 (US3)**: Depends on Phase 2; can run in parallel with US2 after US1 MVP is stable.
- **Phase 6 (Polish)**: Depends on completion of desired user stories.

### User Story Dependencies

- **US1 (P1)**: No dependency on other stories after foundational phase.
- **US2 (P2)**: Depends on US1 chat container existence (`ChatWindow.tsx`) but remains independently testable via mocked events.
- **US3 (P3)**: Depends on app shell foundation; independent from US2 logic.

### Within Each User Story

- Tests first, then implementation.
- Hooks/services before component composition.
- Shared component primitives before app-shell wiring.

---

## Parallel Opportunities

- **Setup**: T003, T004, T005 can run in parallel once T001/T002 complete.
- **Foundational**: T010 and T011 can run in parallel after T007-T009.
- **US1**: T013-T016 parallel test authoring; T017-T019 parallel implementation before T020-T022 integration.
- **US2**: T023 and T024 can run in parallel; T025/T026 sequential in same file.
- **US3**: T028-T030 in parallel; T031 after component completion.
- **Polish**: T032 and T033 parallel.

---

## Parallel Example: User Story 1

```bash
# Parallel test work
Task T013: react_ui/src/hooks/usePdfValidator.test.ts
Task T014: react_ui/src/hooks/useBatchedTokens.test.ts
Task T015: react_ui/src/services/api.test.ts
Task T016: react_ui/src/components/Chat/ChatWindow.test.tsx

# Parallel implementation work
Task T017: react_ui/src/components/Chat/FileUploader.tsx
Task T018: react_ui/src/hooks/useBatchedTokens.ts
Task T019: react_ui/src/components/Chat/MessageList.tsx
```

---

## Parallel Example: User Story 3

```bash
Task T028: react_ui/src/components/Navigation.tsx
Task T029: react_ui/src/components/Quiz/QuizPlaceholder.tsx
Task T030: react_ui/src/components/Evaluation/EvaluationPlaceholder.tsx
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1 and Phase 2.
2. Deliver Phase 3 (US1) end-to-end.
3. Validate US1 independent test and demo chat + PDF upload + streaming.
4. Optionally ship MVP before US2/US3.

### Incremental Delivery

1. Foundation complete (Phases 1-2).
2. Ship US1 (core chat).
3. Add US2 (clarification event handling).
4. Add US3 (navigation scaffolding).
5. Execute Phase 6 polish and verification.

### Suggested Team Parallelization

1. Engineer A: Hooks/services (`useBatchedTokens`, `api.ts`, tests)
2. Engineer B: Chat UI components (`MessageList`, `InputArea`, `FileUploader`)
3. Engineer C: Navigation placeholders + accessibility polish

---

## Notes

- `[P]` tasks touch different files and can execute concurrently.
- Every user story phase is independently testable.
- Keep component code minimal; avoid complex CSS/animation by design.
- Keep event and request schemas centralized in `react_ui/src/schemas.ts` to prevent drift from Python contracts.
