# Feature Specification: React Web UI for AI Tutor

**Feature Branch**: `008-react-ui`
**Created**: 2026-06-18
**Status**: Draft
**Input**: User description: "I want to create a Web interface in React for my AI Tutor application..."

## Clarifications

### Session 2026-06-18

- Q: Which dark-mode visual palette should be used? → A: Option C - dark blue backgrounds with warm golden/amber accents.
- Q: Which markdown rendering library should be used for streamed content? → A: Option A - react-markdown.
- Q: What styling approach should be used for beautification? → A: Option A - Tailwind utility classes only with shared color tokens in one config file.
- Q: Which loading indicator pattern should be used while streaming? → A: Option D - animated dots loader with placeholder progress text.
- Q: How should uploaded files be shown after message submission? → A: Option B - compact attachment chips in the user message bubble, including filename display; user-message rendering extracted as a dedicated component.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Send a Chat Message with PDF Upload (Priority: P1)

A learner opens the AI Tutor web app, types a question about a topic, optionally attaches up to 3 PDF documents, and submits the request. The backend processes the request and streams a teaching response token by token into the chat interface.

**Why this priority**: This is the core value-delivering flow. Without it, the application has no functional purpose.

**Independent Test**: Can be tested end-to-end by opening the app, entering a prompt, uploading a PDF, submitting, and observing streaming text appear in the chat area.

**Acceptance Scenarios**:

1. **Given** the chat page is open and the WebSocket is connected, **When** the user types a message and clicks Send, **Then** the message appears in the chat history and a streaming response begins appearing token-by-token.
2. **Given** the user has attached 1–3 PDFs (each ≤ 20 MB), **When** they submit the request, **Then** the files and prompt are sent together to `/api/chat/request` as multipart form data.
3. **Given** the backend emits `stream-tokens-skt` events with `from_service = "teaching-agent"`, **When** each token arrives over WebSocket, **Then** the token is appended to the current assistant message in the chat view in real time.
4. **Given** the user tries to attach more than 3 PDF files, **When** they attempt to add a fourth, **Then** the UI prevents the selection and shows a clear error message.
5. **Given** the user tries to upload a non-PDF file, **When** they attempt to attach it, **Then** the UI rejects the file and shows a descriptive error message.
6. **Given** a single uploaded file exceeds 20 MB, **When** the user selects it, **Then** the UI rejects the file and displays a size limit error before submission.

---

### User Story 2 - Receive User Level Clarification Prompt (Priority: P2)

When the backend cannot infer the user's knowledge level, it emits a `clarify-user-level-skt` event. The chat interface displays a prompt asking the user to specify their level before the session continues.

**Why this priority**: The clarification flow is part of the live session but can be independently tested against a mock WebSocket.

**Independent Test**: Can be tested by simulating a `clarify-user-level-skt` WebSocket event and verifying the UI renders the appropriate prompt or message in the chat area.

**Acceptance Scenarios**:

1. **Given** the WebSocket is connected and a `clarify-user-level-skt` event arrives, **When** the event is received, **Then** the chat interface displays a clarification prompt to the user.
2. **Given** the event `from_service` field is not `teaching-agent`, **When** a `stream-tokens-skt` event arrives, **Then** the tokens are not rendered in the chat area (ignored for this iteration).

---

### User Story 3 - Scaffold Navigation for Future Sections (Priority: P3)

The application displays three section tabs — Chat, Quiz, and Evaluation. Only the Chat section is functional in this iteration. The other two sections are visible but show a placeholder/coming-soon state.

**Why this priority**: This establishes the navigational skeleton so future iterations can activate sections without structural rework.

**Independent Test**: Can be tested by verifying the three navigation items render correctly and that navigating to Quiz or Evaluation shows a placeholder without errors.

**Acceptance Scenarios**:

1. **Given** the app is loaded, **When** the user views the navigation, **Then** three sections — Chat, Quiz, and Evaluation — are visible.
2. **Given** the user clicks on Quiz or Evaluation, **When** the section renders, **Then** a placeholder or "coming soon" message is shown with no runtime errors.

---

### Edge Cases

- What happens when the WebSocket connection is lost mid-stream? The UI should indicate a disconnected state without crashing.
- What happens when the user submits without a prompt? The submit button should be disabled or show a validation error.
- What happens when the backend returns an error response to `/api/chat/request`? The UI should display an appropriate error message in the chat area.
- What happens when a `stream-tokens-skt` event arrives but `from_service` is not `teaching-agent`? The tokens must be silently ignored without affecting the chat UI.
- What happens when the user submits while a response is already streaming? The submit button should be disabled until the stream completes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The application MUST provide three navigation sections: Chat, Quiz, and Evaluation.
- **FR-002**: Only the Chat section MUST be fully functional in this iteration; Quiz and Evaluation MUST render placeholder content.
- **FR-003**: The Chat section MUST display a header with the title "AI Tutor" and use a dark-blue theme with warm golden/amber accents.
- **FR-004**: The Chat section MUST provide a message input field and a submit button for sending user prompts.
- **FR-005**: The Chat section MUST support attaching up to 3 PDF files per request, with a maximum file size of 20 MB each.
- **FR-006**: The application MUST reject non-PDF file attachments and display a descriptive error to the user.
- **FR-007**: The application MUST reject attachment attempts when the 3-file limit is already reached.
- **FR-008**: User prompts and attached files MUST be submitted together as multipart form data to `/api/chat/request`.
- **FR-009**: The application MUST establish a WebSocket connection to the backend on startup.
- **FR-010**: The application MUST listen to the `stream-tokens-skt` WebSocket event and, when `from_service` equals `"teaching-agent"`, append each token to the current assistant message in the chat view.
- **FR-011**: The application MUST listen to the `clarify-user-level-skt` WebSocket event and display the clarification payload to the user in the chat area.
- **FR-012**: WebSocket events where `from_service` is not `"teaching-agent"` MUST be ignored for chat rendering in this iteration.
- **FR-013**: All backend endpoint URLs, WebSocket URLs, and service identifiers MUST be configurable via environment variables, not hardcoded.
- **FR-014**: Event schemas used by the React app (e.g., `StreamTokensEventBody`, `ClarifyUserLevelEvent`, `WebSocketEvents`) MUST be extracted from the Python schema files and defined in a local TypeScript schema file within the React project.
- **FR-015**: The application MUST follow the UI language and interaction patterns established in the existing Python `ui_frontend` module (chat history list, streaming token accumulation, per-message roles).
- **FR-016**: The submit button MUST be disabled while a streaming response is in progress to prevent duplicate submissions.
- **FR-017**: The application MUST keep component code minimal and avoid complex CSS or animations.
- **FR-018**: The UI color palette tokens MUST be defined in one centralized configuration location to allow fast theme experimentation without editing multiple component files.
- **FR-019**: Streamed assistant content MUST render inside a dedicated text box component that supports Markdown using `react-markdown`.
- **FR-020**: UI beautification MUST use Tailwind CSS utility classes (without additional UI component libraries) to keep implementation minimal and consistent.
- **FR-021**: While awaiting or streaming assistant output, the chat UI MUST show an animated dots loading indicator plus a placeholder progress text area reserved for future backend event-status integration.
- **FR-022**: After a user submits a prompt with files, the corresponding user message bubble MUST display compact attachment chips that include each file's filename.
- **FR-023**: Rendering of user-authored chat messages (including attachment chips) MUST be implemented in a dedicated reusable component to keep message presentation modular.
- **FR-024**: The application MUST include a top navigation bar that prominently displays the product title.
- **FR-025**: The chat interface layout MUST better utilize desktop screen space by using a wider content container while preserving readability.
- **FR-026**: The file upload control MUST be visually styled as an interactive button and maintain clear selected-file feedback before submission.

### Key Entities

- **ChatMessage**: A single entry in the chat history; has a role (`user` or `assistant`), text content, a streaming-complete flag, and optional attachment metadata for user messages (at minimum filename).
- **WebSocket Session**: The live connection to the backend; carries a session ID (`sid`) used to correlate streaming events to the correct browser session.
- **AttachedFile**: A PDF file selected by the user; has a name, size, and binary content to be submitted as form data.
- **StreamTokensEventBody**: `{ from_service: string, sid: string, data: Record<string, any> }` — mirrors the Python schema; `data` carries the token text.
- **ClarifyUserLevelEvent**: `{ request_id: string, user_prompt: string, sid: string, reason?: string }` — mirrors the Python schema.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can submit a chat message with an attached PDF and receive a streaming response within the same browser session without page reloads.
- **SC-002**: 100% of `stream-tokens-skt` events from `teaching-agent` are rendered in the chat area in the order received.
- **SC-003**: File validation errors (wrong type, size exceeded, count exceeded) are surfaced to the user before any network request is made.
- **SC-004**: All three navigation sections (Chat, Quiz, Evaluation) are reachable via the UI with no runtime errors.
- **SC-005**: All backend URLs and WebSocket addresses are environment-variable-driven; no URL is hardcoded in application source.
- **SC-006**: The initial page load and chat interaction are usable on a standard desktop browser at typical broadband speeds without noticeable lag.
- **SC-007**: The refined UI includes a visible top navbar title, Tailwind-styled interactive controls, and a chat layout that uses a wider desktop container without clipping message content.

## Assumptions

- The React application targets modern desktop browsers; mobile responsiveness is not required for this iteration.
- The backend WebSocket server speaks Socket.IO protocol (matching the existing Python `socketio_client.py`); the React client will use `socket.io-client`.
- The `sid` used in form data submissions is the Socket.IO session ID assigned upon connection.
- The `stream-tokens-skt` event payload's `data` field contains a `token` key with the text fragment, consistent with the existing Python frontend behavior.
- The application does not implement authentication; all sessions are anonymous.
- No state persistence (local storage, cookies) is required in this iteration.
- The Quiz and Evaluation sections require no functional code beyond routing placeholders.
- CSS styling will use Tailwind CSS utility classes with centralized theme tokens; additional component UI libraries are out of scope for this iteration.
- The React project will be bootstrapped with Vite for minimal boilerplate.
- The `user_level` field sent with chat requests will default to an empty array, consistent with the backend's `UserRequest` schema default.
