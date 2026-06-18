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
  onDone: () => void;
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
- Must trigger `onDone` when explicit completion is received so parent orchestration can unlock new submissions.

---

## FileUploader

**Purpose**: Accept and validate PDF attachments.

### Props

```typescript
interface FileUploaderProps {
  files: File[];
  errors: string[];
  disabled: boolean;
  onAdd: (files: FileList | null) => void;
  onRemove: (index: number) => void;
}
```

### Contract Rules

- Upload control must be visibly styled as an interactive button.
- Must preserve validation constraints: max 3 files, PDF only, <= 20 MB each.
- Must provide clear selected-file and error feedback.

---

## Style Reuse Contract

All feature components must consume style tokens from:

- `src/styles/theme.ts` for colors/theme constants
- `src/styles/uiClasses.ts` for long/reused Tailwind class strings

No component should define duplicate long class compositions already present in `uiClasses.ts`.
