# Data Model: React UI Streaming-State Refactor

**Phase**: Phase 1 — Design
**Feature**: `specs/006-react-ui`
**Date**: 2026-06-18

All entities below are TypeScript types. Their canonical source is `react_ui/src/schemas.ts` for UI-local types and the noted Python files for mirrored contracts.

---

## Entities

### ChatMessage *(UI-local)*

Represents a single entry in the chat history list.

| Field | Type | Description |
|---|---|---|
| `id` | `string` | UUID generated at creation time; used as React key |
| `role` | `'user' \| 'assistant'` | Message origin |
| `content` | `string` | Stable content for user/info messages; assistant stream content is maintained in `StreamResponseBox` |
| `isStreaming` | `boolean` | Assistant stream lifecycle marker used by rendering layer |
| `attachments` | `Array<{ name: string; sizeBytes: number }>` (optional) | Metadata for user attachment chips |

**Validation rules**:
- `id` must be unique within the session's message list.
- For assistant stream entries, `content` may remain empty because stream text state is local to `StreamResponseBox`.

**State transitions**:
```text
assistant stream entry created -> StreamResponseBox appends token fragments -> done=true marks stream completion
```

---

### AttachedFile *(UI-local)*

Represents a PDF file selected by the user before submission. Not persisted; discarded after successful form submission.

| Field | Type | Description |
|---|---|---|
| `file` | `File` | Native browser File object |
| `name` | `string` | `file.name` — displayed in the UI |
| `sizeBytes` | `number` | `file.size` — used for 20 MB validation |

**Validation rules**:
- `file.type` must equal `'application/pdf'`
- `file.size` must be ≤ `20 * 1024 * 1024` bytes (20 MB)
- Total `AttachedFile[]` length must be ≤ 3

---

### StreamTokensEventBody *(mirrored from `project/schemas.py`)*

Payload shape of the `stream-tokens-skt` Socket.IO event emitted by the backend.

| Field | Type | Description |
|---|---|---|
| `from_service` | `string` | Name of the producing agent (e.g., `"teaching-agent"`) |
| `sid` | `string` | Socket.IO session ID for routing to the correct client |
| `data` | `Record<string, any>` | Agent-specific payload; for teaching-agent includes token fragments and completion metadata |

**Teaching-agent `data` patterns**:
- `{ token: string }` for streaming fragments
- `{ done: true, tokens_used?: number }` for explicit completion

**Routing rule**: Only render in Chat if `from_service === "teaching-agent"` and `sid` matches the browser session.

---

### ClarifyUserLevelEvent *(mirrored from `project/schemas.py`)*

Payload shape of the `clarify-user-level-skt` Socket.IO event.

| Field | Type | Description |
|---|---|---|
| `request_id` | `string` | Unique request identifier |
| `user_prompt` | `string` | The original user prompt |
| `sid` | `string` | Socket.IO session ID |
| `reason` | `string` (optional) | Why level could not be inferred |

---

### UserRequest *(mirrored from `project/schemas.py`)*

Fields submitted as multipart form data to `/api/chat/request`.

| Field | Type | Form encoding |
|---|---|---|
| `user_prompt` | `string` | Single `user_prompt` form field |
| `user_level` | `string[]` | Repeated `user_level` form keys (default: `[]`) |
| `sid` | `string` | Single `sid` form field |
| `files` | `File[]` | Repeated `files` file inputs (0–3 PDFs) |

---

### WebSocket Event Names *(mirrored from `project/events.py`)*

| Constant | Value | Direction |
|---|---|---|
| `STREAM_TOKENS_SKT` | `"stream-tokens-skt"` | Backend → Frontend |
| `CLARIFY_USER_LEVEL_SKT` | `"clarify-user-level-skt"` | Backend → Frontend |

---

## State Shape — App-Level

The App component manages minimal state:

```typescript
// App.tsx
type Section = 'chat' | 'quiz' | 'evaluation';

interface AppState {
  currentSection: Section;        // Active navigation section
  socketId: string | null;        // socket.id once connected
}
```

---

## State Shape — Chat Section

Managed locally within `ChatWindow.tsx`:

```typescript
interface ChatState {
  messages: ChatMessage[];        // Full history
  attachedFiles: AttachedFile[];  // Pending uploads
  inputText: string;              // Current draft
  isSubmitting: boolean;          // Request in-flight (disables submit)
  fileErrors: string[];           // Validation errors from usePdfValidator
}
```

Managed locally within `StreamResponseBox.tsx`:

```typescript
interface StreamResponseState {
  markdownContent: string;
  isStreaming: boolean;
  progressPlaceholder: string;
  tokensUsed: number | null;
}
```

Completion transition:

```text
on token fragment -> append markdownContent
on done=true -> set isStreaming=false and capture tokens_used
```

---

## Relationships

```
App
 ├─ socket singleton (1 per session)
 ├─ Navigation (reads/writes currentSection)
 └─ ChatWindow (message list orchestration)
  ├─ MessageList
  │   ├─ UserMessage
  │   └─ StreamResponseBox (owns teaching-agent stream state)
  ├─ InputArea
  └─ FileUploader
```
