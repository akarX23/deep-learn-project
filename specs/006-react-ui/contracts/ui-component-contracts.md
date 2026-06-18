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

**Purpose**: Render assistant streamed content with markdown and loading state.

### Props

```typescript
interface StreamResponseBoxProps {
  markdownContent: string;
  isStreaming: boolean;
  progressPlaceholder: string;
}
```

### Contract Rules

- Must render markdown via `react-markdown`.
- While `isStreaming` is true, show animated dots loader.
- Must show progress placeholder text region for future backend progress events.

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
