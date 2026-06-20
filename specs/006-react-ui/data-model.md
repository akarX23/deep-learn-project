# Data Model: React UI Stream Completion Persistence + Upload Control Refinement

**Phase**: Phase 1 — Design
**Feature**: `specs/006-react-ui`
**Date**: 2026-06-18

All entities below are TypeScript types. Canonical implementation sources are `react_ui/src/schemas.ts` and chat component interfaces.

---

## Entities

### ChatMessage *(UI-local)*

Represents one entry in the chat history.

| Field | Type | Description |
|---|---|---|
| `id` | `string` | UUID/key for list reconciliation |
| `role` | `'user' \| 'assistant'` | Message origin |
| `content` | `string` | User text or persisted finalized assistant markdown |
| `isStreaming` | `boolean` | Assistant stream lifecycle marker |
| `tokens_used` | `number` (optional) | Persisted completion usage metric for assistant messages |
| `attachments` | `Array<{ name: string; sizeBytes: number }>` (optional) | User file-chip metadata |
| `info` | `boolean` (optional) | Clarification/error informational styling marker |

**Validation rules**:
- `id` must be unique within message list.
- `tokens_used` is only valid for completed assistant messages.

**Lifecycle**:
```text
assistant placeholder created (isStreaming=true, content='')
 -> StreamResponseBox appends local token fragments
 -> done=true triggers completion callback {messageId, fullContent, tokens_used}
 -> ChatWindow persists content/tokens_used and sets isStreaming=false
```

---

### StreamCompletionPayload *(UI-local callback contract)*

Payload emitted from `StreamResponseBox` to `ChatWindow` when explicit completion arrives.

| Field | Type | Description |
|---|---|---|
| `messageId` | `string` | Assistant message identity to finalize |
| `fullContent` | `string` | Complete markdown content assembled from token stream |
| `tokens_used` | `number` (optional) | Usage metadata from completion payload |

**Validation rules**:
- Only emitted when `data.done === true` for teaching-agent stream.
- `messageId` must match an existing assistant message in chat state.

---

### AttachedFile *(UI-local)*

Represents a selected PDF before submit.

| Field | Type | Description |
|---|---|---|
| `file` | `File` | Browser file object |
| `name` | `string` | Display name |
| `sizeBytes` | `number` | Upload validation basis |

**Validation rules**:
- MIME type must be PDF.
- Max 3 files.
- Max 20 MB each.

---

### StreamTokensEventBody *(mirrored from backend schema)*

| Field | Type | Description |
|---|---|---|
| `from_service` | `string` | Must be `teaching-agent` for chat render path |
| `sid` | `string` | Session routing key |
| `data.token` | `string` (optional) | Stream fragment |
| `data.done` | `boolean` (optional) | Explicit completion marker |
| `data.tokens_used` | `number` (optional) | Completion usage metric |

---

### ClarifyUserLevelEvent *(mirrored from backend schema)*

| Field | Type | Description |
|---|---|---|
| `request_id` | `string` | Request identifier |
| `user_prompt` | `string` | Original learner prompt |
| `sid` | `string` | Session ID |
| `reason` | `string` (optional) | Clarification reason |

---

## State Shape — App-Level

```typescript
type Section = 'chat' | 'quiz' | 'evaluation';

interface AppState {
  currentSection: Section;
  socketId: string | null;
}
```

## State Shape — ChatWindow

```typescript
interface ChatState {
  messages: ChatMessage[];
  activeStreamMessageId: string | null;
  attachedFiles: AttachedFile[];
  inputText: string;
  isSubmitting: boolean;
  fileErrors: string[];
}
```

`ChatWindow` owns structural message state and final persisted completion payload.

## State Shape — StreamResponseBox

```typescript
interface StreamResponseState {
  markdownContent: string;
  isStreaming: boolean;
  tokensUsed: number | null;
  progressPlaceholder: string;
}
```

`StreamResponseBox` owns high-frequency streaming updates until completion callback handoff.

---

## Relationships

```text
App
 ├─ socket singleton
 ├─ Navigation
 └─ ChatWindow
    ├─ MessageList
    │   ├─ UserMessage
    │   └─ StreamResponseBox --onDone--> ChatWindow (StreamCompletionPayload)
    ├─ InputArea
    └─ FileUploader
```
