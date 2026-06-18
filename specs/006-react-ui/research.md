# Research: React UI Refresh for Feature 006

**Phase**: Phase 0 — Technology Research  
**Feature**: `specs/006-react-ui`  
**Branch**: `008-react-ui`  
**Date**: 2026-06-18

## Summary

All planning unknowns are resolved. The design keeps boilerplate low, preserves Tailwind-based theming, and introduces direct event-driven streaming in `StreamResponseBox` without batched delays.

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

**Decision**: Render assistant stream text through `react-markdown` in `StreamResponseBox`, which owns teaching-agent stream updates.

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

## 5. Explicit Completion Event Handling

**Decision**: End stream only when `stream-tokens-skt` payload includes `data.done === true` from `teaching-agent`.

**Rationale**: Timer-based completion can drop or mis-sequence late packets. Explicit completion removes ambiguity and eliminates timeout tuning.

**Alternatives considered**:
- Inactivity timeout completion: susceptible to jitter and packet timing variance.
- Completion on next user submit: can keep stale stream open too long.

## 6. Token Usage Rendering

**Decision**: Render `data.tokens_used` as a small secondary line under each `StreamResponseBox` when completion payload provides it.

**Rationale**: Provides immediate cost/usage context without cluttering primary assistant text.

**Alternatives considered**:
- Show in separate global area: weak message-to-usage association.
- Omit usage display: loses useful feedback requested by stakeholders.

## 7. Stream State Ownership Boundary

**Decision**: Move teaching-agent stream state (token aggregation, completion state, placeholder progression, tokens-used display) into `StreamResponseBox`; keep `ChatWindow` focused on message list orchestration.

**Rationale**: Limits high-frequency rerenders to one component and improves responsiveness under rapid token flow.

**Alternatives considered**:
- Keep stream state in `ChatWindow`: causes broad rerenders and event handling contention.
- Shared global stream store: unnecessary complexity for current single-chat scope.

## 8. Attachment Display Pattern in Chat History

**Decision**: Show compact file chips (filename visible) inside user message bubbles after submit.

**Rationale**: Preserves request context directly in chat history and satisfies clarified requirement.

**Alternatives considered**:
- Keep attachments only in pre-submit picker: Context is lost after sending.
- Plain text filenames: Lower visual scanability.

## 9. Component Decomposition for Maintainability

**Decision**: Extract user-authored message rendering to dedicated reusable component (`UserMessage`) and keep stream display concerns in dedicated response box component.

**Rationale**: Enforces separation of concerns and simplifies targeted tests.

**Alternatives considered**:
- Keep all rendering in `MessageList`: Grows into monolith as visual rules expand.

## 10. Layout and Space Utilization

**Decision**: Expand content container width for desktop while preserving readable line-length constraints and responsive behavior.

**Rationale**: Better use of available screen space without harming readability.

**Alternatives considered**:
- Fixed narrow container: Wastes horizontal space.
- Full-width everything: Can reduce readability for long text.

## 11. Existing Runtime Contract Stability

**Decision**: Keep REST contract unchanged and extend Socket.IO payload interpretation for explicit completion metadata (`done`, `tokens_used`) while preserving event names and core shape.

**Rationale**: Limits risk and avoids backend coordination for this iteration.

**Alternatives considered**:
- Introduce new backend progress events now: Useful later, but out of current scope.
