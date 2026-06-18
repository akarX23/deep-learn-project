# Research: React UI Refresh for Feature 006

**Phase**: Phase 0 — Technology Research  
**Feature**: `specs/006-react-ui`  
**Branch**: `008-react-ui`  
**Date**: 2026-06-18

## Summary

All planning unknowns are resolved. The design keeps boilerplate low while adding a cleaner dark-mode UI and reusable Tailwind class strategy.

## 1. Tailwind Styling Strategy with Minimal Boilerplate

**Decision**: Use Tailwind CSS utilities only (no component UI libraries) and keep repeated long class strings in a single reusable module: `src/styles/uiClasses.ts`.

**Rationale**: Tailwind gives fast styling with low ceremony. Centralizing verbose class combinations avoids noisy JSX and supports clean experimentation.

**Alternatives considered**:
- Component library (e.g., MUI/Chakra): Adds dependency and abstraction overhead.
- Ad hoc inline classes everywhere: Fast initially but hard to maintain.

## 2. Centralized Theme Tokens

**Decision**: Define dark blue + amber design tokens in one place (`src/styles/theme.ts`) and reference them from `uiClasses.ts` and targeted inline values only where necessary.

**Rationale**: The spec requires single-point color configuration for future experimentation.

**Alternatives considered**:
- Scatter colors across components: Violates FR-018 and increases drift risk.
- Heavy theming system: Unnecessary complexity for current scope.

## 3. Markdown Rendering for Streamed Assistant Output

**Decision**: Render assistant stream text through `react-markdown` in a dedicated stream content box component.

**Rationale**: Native React markdown rendering with minimal setup and good compatibility with incremental token updates.

**Alternatives considered**:
- `marked` + sanitizer: Extra integration complexity.
- `remark`/`rehype` custom pipeline: More flexible but heavier than needed.

## 4. Loading and Progress Placeholder UX

**Decision**: Use animated dots loader with a progress placeholder text slot (future backend event integration point).

**Rationale**: Meets clarified UX requirement while remaining simple to implement and test.

**Alternatives considered**:
- Spinner only: No explicit progress affordance.
- Full skeleton system: More boilerplate for limited benefit.

## 5. Attachment Display Pattern in Chat History

**Decision**: Show compact file chips (filename visible) inside user message bubbles after submit.

**Rationale**: Preserves request context directly in chat history and satisfies clarified requirement.

**Alternatives considered**:
- Keep attachments only in pre-submit picker: Context is lost after sending.
- Plain text filenames: Lower visual scanability.

## 6. Component Decomposition for Maintainability

**Decision**: Extract user-authored message rendering to dedicated reusable component (`UserMessage`) and keep stream display concerns in dedicated response box component.

**Rationale**: Enforces separation of concerns and simplifies targeted tests.

**Alternatives considered**:
- Keep all rendering in `MessageList`: Grows into monolith as visual rules expand.

## 7. Layout and Space Utilization

**Decision**: Expand content container width for desktop while preserving readable line-length constraints and responsive behavior.

**Rationale**: Better use of available screen space without harming readability.

**Alternatives considered**:
- Fixed narrow container: Wastes horizontal space.
- Full-width everything: Can reduce readability for long text.

## 8. Existing Runtime Contract Stability

**Decision**: Keep existing REST and Socket.IO contracts unchanged (`/api/chat/request`, `stream-tokens-skt`, `clarify-user-level-skt`), and apply UI updates client-side only.

**Rationale**: Limits risk and avoids backend coordination for this iteration.

**Alternatives considered**:
- Introduce new backend progress events now: Useful later, but out of current scope.
