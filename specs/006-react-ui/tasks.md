# Tasks: React UI Refresh (Dark Theme + Tailwind Reuse)

**Input**: Design documents from `/specs/006-react-ui/`  
**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: No explicit test tasks are generated because the current feature specification does not explicitly request TDD or test-first tasks for this iteration.

**Organization**: Tasks are grouped by user story to keep each story independently implementable and verifiable.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Install styling/rendering dependencies and baseline frontend configuration.

- [X] T001 Install Tailwind build dependencies in `react_ui/package.json`
- [X] T002 Install markdown renderer dependency in `react_ui/package.json`
- [X] T003 Configure Tailwind and PostCSS in `react_ui/tailwind.config.js` and `react_ui/postcss.config.js`
- [X] T004 Add Tailwind directives to stylesheet in `react_ui/src/index.css`
- [X] T005 Ensure app entry imports shared stylesheet in `react_ui/src/main.tsx`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build shared style/system primitives used by all stories.

**⚠️ CRITICAL**: No user story work starts before this phase completes.

- [X] T006 Create centralized color and spacing tokens in `react_ui/src/styles/theme.ts`
- [X] T007 Create reusable Tailwind class registry in `react_ui/src/styles/uiClasses.ts`
- [X] T008 [P] Extend chat message schema for attachment metadata in `react_ui/src/schemas.ts`
- [X] T009 [P] Add shared markdown stream response box component in `react_ui/src/components/Chat/StreamResponseBox.tsx`
- [X] T010 Add shared loading indicator component with placeholder text slot in `react_ui/src/components/Chat/LoadingIndicator.tsx`
- [X] T011 Create dedicated user message presentation component in `react_ui/src/components/Chat/UserMessage.tsx`

**Checkpoint**: Shared theme, class reuse, and message primitives are ready for story implementation.

---

## Phase 3: User Story 1 - Send a Chat Message with PDF Upload (Priority: P1) 🎯 MVP

**Goal**: Deliver beautified chat flow with PDF upload, markdown streaming, loading animation, and attachment chips in sent user messages.

**Independent Test**: User submits a prompt with 0-3 valid PDFs and sees dark-themed chat, markdown-rendered assistant stream, animated dots while streaming, and filename chips on the corresponding user message.

- [X] T012 [P] [US1] Refactor message list to use dedicated user message component in `react_ui/src/components/Chat/MessageList.tsx`
- [X] T013 [US1] Render attachment chips with filename in user message UI in `react_ui/src/components/Chat/UserMessage.tsx`
- [X] T014 [US1] Integrate markdown stream box for assistant output in `react_ui/src/components/Chat/MessageList.tsx`
- [X] T015 [US1] Integrate animated dots loader and progress placeholder in `react_ui/src/components/Chat/ChatWindow.tsx`
- [X] T016 [US1] Persist submitted file metadata onto user message objects in `react_ui/src/components/Chat/ChatWindow.tsx`
- [X] T017 [US1] Replace inline chat styles with reusable Tailwind class tokens in `react_ui/src/components/Chat/ChatWindow.tsx`
- [X] T018 [US1] Beautify input and submit controls with shared Tailwind classes in `react_ui/src/components/Chat/InputArea.tsx`
- [X] T019 [US1] Beautify file upload button and file list styling in `react_ui/src/components/Chat/FileUploader.tsx`
- [X] T020 [US1] Keep multipart request and sid wiring stable after UI refactor in `react_ui/src/services/api.ts` and `react_ui/src/components/Chat/ChatWindow.tsx`

**Checkpoint**: User Story 1 is fully functional and independently demoable as the MVP.

---

## Phase 4: User Story 2 - Receive User Level Clarification Prompt (Priority: P2)

**Goal**: Preserve and polish clarification behavior within the refreshed chat experience.

**Independent Test**: Simulate `clarify-user-level-skt` and non-teaching `stream-tokens-skt` events; clarification appears as styled info content and non-teaching stream tokens remain ignored.

- [X] T021 [US2] Style clarification/info messages with dark-theme visual language in `react_ui/src/components/Chat/MessageList.tsx`
- [X] T022 [US2] Preserve non-teaching-agent token ignore logic in `react_ui/src/components/Chat/ChatWindow.tsx`
- [X] T023 [US2] Ensure clarification rendering path remains compatible with markdown stream UI in `react_ui/src/components/Chat/ChatWindow.tsx`

**Checkpoint**: Clarification flow is independently verifiable and remains behaviorally correct.

---

## Phase 5: User Story 3 - Scaffold Navigation for Future Sections (Priority: P3)

**Goal**: Provide a polished app shell with navbar/title and improved section layout while keeping Quiz/Evaluation as placeholders.

**Independent Test**: User sees a top navbar title, can switch across Chat/Quiz/Evaluation, and views styled placeholders for non-chat sections without runtime errors.

- [X] T024 [P] [US3] Create top navbar component with title display in `react_ui/src/components/Navbar.tsx`
- [X] T025 [US3] Integrate navbar and wider responsive container layout in `react_ui/src/App.tsx`
- [X] T026 [P] [US3] Apply Tailwind dark-theme styling to section navigation in `react_ui/src/components/Navigation.tsx`
- [X] T027 [P] [US3] Beautify quiz placeholder surface in `react_ui/src/components/Quiz/QuizPlaceholder.tsx`
- [X] T028 [P] [US3] Beautify evaluation placeholder surface in `react_ui/src/components/Evaluation/EvaluationPlaceholder.tsx`

**Checkpoint**: App shell and section navigation are polished and independently usable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final consistency, documentation, and validation updates across stories.

- [X] T029 [P] Update implementation notes for shared theme/class-token reuse in `specs/006-react-ui/quickstart.md`
- [X] T030 [P] Sync API contract notes with refreshed UI behavior in `specs/006-react-ui/contracts/api-contracts.md`
- [X] T031 [P] Sync component contracts with implemented props and responsibilities in `specs/006-react-ui/contracts/ui-component-contracts.md`
- [X] T032 Validate accessibility labels, focus order, and disabled/loading states in `react_ui/src/components/Chat/InputArea.tsx`, `react_ui/src/components/Chat/FileUploader.tsx`, and `react_ui/src/components/Navigation.tsx`
- [ ] T033 Run full local quality gates from `react_ui/package.json` scripts and resolve surfaced issues across `react_ui/src/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Starts immediately.
- **Phase 2 (Foundational)**: Depends on Phase 1 and blocks all user stories.
- **Phase 3 (US1)**: Depends on Phase 2; defines MVP delivery.
- **Phase 4 (US2)**: Depends on Phase 2 and builds on chat event handling.
- **Phase 5 (US3)**: Depends on Phase 2 and can proceed in parallel with US2 if staffing allows.
- **Phase 6 (Polish)**: Depends on completion of selected user stories.

### User Story Dependencies

- **US1 (P1)**: No dependency on other stories after Foundational phase.
- **US2 (P2)**: Depends on US1 chat event/rendering surfaces but remains independently testable via event simulation.
- **US3 (P3)**: Depends on shared app shell/state only; independent of US2 event logic.

### Within Each User Story

- Build core components before integrating into container components.
- Keep schema/service compatibility before final UI wiring.
- Complete each story's checkpoint before moving to next priority.

---

## Parallel Opportunities

- Phase 2: `T008` and `T009` can run in parallel after `T006` and `T007`.
- US1: `T012` and `T019` can run in parallel; `T017` and `T018` can run in parallel before final integration tasks.
- US3: `T024`, `T026`, `T027`, and `T028` can run in parallel before `T025` final app-shell integration.
- Phase 6: `T029`, `T030`, and `T031` can run in parallel.

---

## Parallel Example: User Story 1

```bash
# Parallel UI work in separate files
Task T012: react_ui/src/components/Chat/MessageList.tsx
Task T019: react_ui/src/components/Chat/FileUploader.tsx

# Parallel style cleanup in separate files
Task T017: react_ui/src/components/Chat/ChatWindow.tsx
Task T018: react_ui/src/components/Chat/InputArea.tsx
```

---

## Parallel Example: User Story 3

```bash
Task T024: react_ui/src/components/Navbar.tsx
Task T026: react_ui/src/components/Navigation.tsx
Task T027: react_ui/src/components/Quiz/QuizPlaceholder.tsx
Task T028: react_ui/src/components/Evaluation/EvaluationPlaceholder.tsx
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 (US1).
3. Validate US1 independent test criteria and demo chat refresh.
4. Ship MVP.

### Incremental Delivery

1. Foundation complete (Phases 1-2).
2. Deliver US1 (core chat refresh).
3. Deliver US2 (clarification behavior in refreshed UI).
4. Deliver US3 (navbar and scaffold polish).
5. Finish Phase 6 cross-cutting validation and docs sync.

### Parallel Team Strategy

1. One developer handles style infrastructure (`theme.ts`, `uiClasses.ts`, shared components).
2. One developer handles chat interaction integration (`ChatWindow`, `MessageList`, `api.ts`).
3. One developer handles app shell/navigation polish (`Navbar`, `Navigation`, placeholders).

---

## Notes

- `[P]` tasks are designed for parallel execution with file-level isolation.
- Story labels are only applied to user-story phases.
- Each user story remains independently verifiable.
- Keep implementation minimal and avoid introducing unnecessary abstraction layers.
