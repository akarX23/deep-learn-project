# Specification Quality Checklist: Teaching Agent

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-05-28
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Phase 1 checklist items above all pass. Core pipeline spec is complete.
- Python is mentioned in FR-013/FR-014 as the expected example language — this is a product-level assumption documented in Assumptions, not an implementation detail imposed on the agent internals.
- The Evaluation Agent is referenced as a downstream consumer but is not yet specified; its contract with `TeachingCompletionEvent` should be confirmed before it is implemented.

## Phase 2 — Kafka Integration (added 2026-06-13)

Kafka integration requirements FR-019 – FR-028 and success criteria SC-008 – SC-010 have been added to `spec.md`. The items below should be re-validated before Phase 2 implementation begins.

- [x] Kafka topic names registered in `project/topics.py`: `"teaching"` under `PlannerTopics.TEACHING`; `"teaching-complete"` under `TeachingTopics.TEACHING_COMPLETE`
- [x] `TeachingRequestEvent` and `TeachingCompletionEvent` schemas defined in `data-model.md` and `contracts/teaching-agent-contract.md`
- [x] Always-publish rule documented (SC-009): completion event published on both success and error
- [x] `request_id`, `sid`, and `user_level` pass-through rules documented (FR-022, FR-023, SC-008)
- [x] Malformed payload handling documented (FR-028, SC-010)
- [x] Three-file Kafka structure mandated (FR-027) consistent with RAG agent pattern
- [x] Test isolation requirement documented: injectable factories, no real Kafka in tests
- [x] Downstream consumer (Quiz Agent, Planner) contract for `TeachingCompletionEvent` confirmed: Phase 4 changes `content` from JSON-serialized `TeachingContent` to raw markdown string — downstream agents updated accordingly

## Phase 4 — Token Streaming (added 2026-06-16)

Token streaming requirements FR-029 – FR-035 and success criteria SC-011 – SC-013 have been added to `spec.md`. The items below should be validated before Phase 4 implementation begins.

- [x] `"stream-tokens"` Kafka topic registered in `project/topics.py` as `BackendStreamTopics.STREAM_TOKENS`
- [x] `StreamTokensEventBody` schema defined in `project/schemas.py`
- [x] Markdown output format and bold section headers documented in `spec.md` (FR-029) and `contracts/teaching-agent-contract.md`
- [x] Field streaming rules documented: explanation/notes/example streamed per chunk; diagram buffered and sent complete (FR-031, SC-013)
- [x] Stream-complete sentinel design documented (FR-032, Decision 16 in `research.md`)
- [x] `TeachingCompletionEvent.content` format change documented (FR-034, Decision 17 in `research.md`)
- [x] `StreamingFieldExtractor` design documented (Decision 15 in `research.md`)
- [x] Diagram retry path (beginner mode) confirmed non-streaming — retry tokens not published to `"stream-tokens"`
- [ ] `StreamingFieldExtractor` unit tests written and passing before agent.py wiring begins (T042 before T039)
- [ ] Full test suite passes after all Phase 4 implementation tasks complete (T046)
