# Research: React UI Stream Completion Persistence + Upload Control Refinement

**Phase**: Phase 0 — Technology Research  
**Feature**: `specs/006-react-ui`  
**Branch**: `008-react-ui`  
**Date**: 2026-06-18

## Summary

All planning unknowns are resolved. The refined design keeps minimal boilerplate while ensuring completed stream content cannot reset and upload controls are compact and clear.

## 1. Completion Persistence Handoff

**Decision**: On `data.done === true`, `StreamResponseBox` emits `{ messageId, fullContent, tokens_used }` to `ChatWindow` via completion callback.

**Rationale**: Local stream state is ideal for high-frequency updates, but finalized content must be persisted in message-list state to prevent reset on rerender/remount.

**Alternatives considered**:
- Keep only local state in `StreamResponseBox`: risks reset when component lifecycle changes.
- Keep full stream state in `ChatWindow`: increases parent rerenders and weakens ownership boundary.

## 2. Explicit Completion Semantics

**Decision**: Completion remains strictly event-driven (`data.done === true`) with no timeout fallback.

**Rationale**: Timeout completion is non-deterministic under network jitter and can finalize too early.

**Alternatives considered**:
- Inactivity timeout: brittle under variable packet cadence.
- Mixed timeout + done logic: more complexity with ambiguous precedence.

## 3. Token Usage Persistence

**Decision**: Persist optional `tokens_used` on `ChatMessage` after completion and render it in secondary text below the response box.

**Rationale**: Ties usage data to its exact response and preserves value after rerenders/navigation.

**Alternatives considered**:
- Keep usage only transiently in component-local state: metadata may be lost.
- Show usage in global header: weak context association.

## 4. Stream State Ownership Boundary

**Decision**: Keep live token accumulation in `StreamResponseBox`, with `ChatWindow` handling only message structure/lifecycle.

**Rationale**: Preserves responsiveness and clean separation of concerns.

**Alternatives considered**:
- Parent-managed token updates: broader rerender impact.
- Global store for streaming: over-engineering for current scope.

## 5. Compact Upload Control UX

**Decision**: Render a small attachment-style upload trigger (icon + `Upload`) below textarea with adjacent helper text for limits.

**Rationale**: Reduces visual clutter while keeping affordance and constraints visible.

**Alternatives considered**:
- Full-size explicit upload button and separate heading: more chrome than needed.
- Icon-only upload control: less discoverable for new users.

## 6. Chat Header Simplification

**Decision**: Remove redundant in-panel "Ask AI Tutor" heading and rely on navbar title + textarea placeholder.

**Rationale**: Avoid duplicated hierarchy and keep chat surface focused on interaction.

**Alternatives considered**:
- Keep both navbar title and panel heading: repetitive and visually noisy.

## 7. Styling Strategy and Reuse

**Decision**: Continue Tailwind-only approach with centralized `theme.ts` and `uiClasses.ts` reuse.

**Rationale**: Meets minimal-boilerplate constraint while maintaining consistency across updated chat controls.

**Alternatives considered**:
- Introduce component library: unnecessary dependency overhead.

## 8. Compatibility with Existing Backend Contracts

**Decision**: Preserve existing endpoint/event names and consume additive payload fields (`done`, `tokens_used`) without backend schema breakage.

**Rationale**: Enables frontend refinement with low integration risk.

**Alternatives considered**:
- Introduce new event type for completion summary: not required for current scope.
