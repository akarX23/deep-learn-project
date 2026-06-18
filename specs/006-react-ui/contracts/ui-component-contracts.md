# UI Component Contracts: React UI Refresh

**Phase**: Phase 1 — Design  
**Feature**: `specs/006-react-ui`  
**Date**: 2026-06-18

This document defines internal component interface contracts used to keep the UI refactor modular and low-boilerplate.

---

## Navbar

**Purpose**: Display product title and top-level visual identity.

### Props

```typescript
interface NavbarProps {
  title: string; // e.g., "AI Tutor"
}
```

### Contract Rules

- Must render as top app bar.
- Must use centralized theme tokens/class registry.
- Must not own application state.

---

## UserMessage

**Purpose**: Render user-authored chat messages and attachment chips.

### Props

```typescript
interface UserMessageProps {
  content: string;
  attachments?: Array<{
    name: string;
    sizeBytes?: number;
  }>;
}
```

### Contract Rules

- Must render message content text.
- If attachments exist, must render compact chips with filename visible.
- Should keep structure presentation-only (no network or socket side effects).

---

## StreamResponseBox

**Purpose**: Own teaching-agent stream state and render assistant streamed markdown content with loading and completion metadata.

### Props

```typescript
interface StreamResponseBoxProps {
  sid: string | null;
  messageId: string;
  isActive: boolean;
  initialContent: string;
  progressPlaceholder: string;
  onDone: (payload: {
    messageId: string;
    fullContent: string;
    tokens_used?: number;
  }) => void;
}
```

### Contract Rules

- Must subscribe to `stream-tokens-skt` teaching-agent packets for matching `sid`.
- Must process stream packets only when `isActive` is true for the current assistant message.
- Must maintain local stream state (markdown text, completion flag, tokens-used value).
- Must render markdown via `react-markdown` with no batching delay.
- Must mark completion only when payload contains `data.done === true`.
- Must display `tokens_used` as small secondary text below markdown content when provided.
- Must show progress placeholder text while streaming.
- Must trigger `onDone` when explicit completion is received and include `messageId`, finalized `fullContent`, and optional `tokens_used` so parent state persists completion results.

---

## InputArea

**Purpose**: Render the prompt text area and send action with minimal chrome.

### Contract Rules

- Must rely on text area placeholder for prompt guidance.
- Must not render a redundant in-panel "Ask AI Tutor" heading when navbar title is present.

---

## FileUploader

**Purpose**: Accept and validate PDF attachments with compact controls.

### Contract Rules

- Upload trigger must be compact and attachment-style (icon + `Upload` label).
- Upload control must appear below the text area.
- Helper text near upload control must indicate limits (max 3 PDFs, 20 MB each).
- Validation constraints remain unchanged: PDF-only, max 3 files, <= 20 MB each.

---

## Style Reuse Contract

All feature components must consume style tokens from:

- `src/styles/theme.ts` for colors/theme constants
- `src/styles/uiClasses.ts` for long/reused Tailwind class strings

No component should define duplicate long class compositions already present in `uiClasses.ts`.
