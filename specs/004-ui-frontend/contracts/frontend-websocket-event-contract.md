# Contract: Frontend WebSocket Event Protocol

## Purpose

Define the backend-to-frontend websocket contract for real-time tutoring events.

## Connection Contract

- Endpoint is configured through environment variable(s).
- Frontend auto-connects on startup.
- Frontend exposes connection lifecycle states:
  - `connecting`
  - `connected`
  - `reconnecting`
  - `disconnected`
  - `failed`
- Unexpected disconnect MUST trigger reconnect attempt initiation within 2 seconds.

## Event Envelope (Required)

All websocket messages MUST match this envelope:

```json
{
  "schema_version": "1.0",
  "event_id": "evt-123",
  "event_type": "teaching.token",
  "source_agent": "teaching-agent",
  "session_id": "sess-abc",
  "request_id": "req-xyz",
  "timestamp": "2026-06-11T10:00:00Z",
  "payload": {},
  "status": "ok",
  "error_message": null
}
```

Required field rules:
- `event_type`, `source_agent`, `session_id`, `timestamp`, and `payload` are mandatory.
- Messages failing envelope validation MUST NOT be routed to business views.

## Supported Event Types and Payload Contracts

### teaching.token
Payload:

```json
{
  "stream_id": "stream-1",
  "sequence": 0,
  "token": "Gradient",
  "is_final": false
}
```

### teaching.complete
Payload:

```json
{
  "stream_id": "stream-1",
  "final_text": "...",
  "tokens_used": 420
}
```

### planner.status
Payload:

```json
{
  "stage": "dispatch_agents",
  "message": "Planner dispatched downstream agents",
  "progress_percent": 55
}
```

### quiz.started | quiz.question | quiz.feedback | quiz.completed
Payload examples:

```json
{
  "quiz_id": "quiz-7",
  "phase": "question",
  "question_text": "What is Big-O?",
  "choices": ["A", "B", "C"],
  "feedback": null,
  "score": null
}
```

### evaluation.result
Payload:

```json
{
  "evaluation_id": "eval-4",
  "summary": "Good conceptual understanding",
  "strengths": ["Terminology", "Reasoning"],
  "gaps": ["Edge cases"],
  "recommendations": ["Practice complexity analysis"]
}
```

### system.error
Payload:

```json
{
  "code": "RELAY_FAILURE",
  "message": "Relay temporarily unavailable",
  "retryable": true
}
```

## Routing Contract

- `teaching.token`, `teaching.complete` -> Chat tab state/view.
- `planner.status` -> Status panel.
- `quiz.*` -> Quiz tab state/view.
- `evaluation.result` -> Evaluation tab state/view.
- `system.error` and unsupported types -> diagnostics collection (optional status warning display).

## Ordering and Idempotency

- Teaching token events SHOULD include monotonic `sequence` per `stream_id`.
- Duplicate chunks (same `stream_id` + `sequence`) MUST be ignored after first successful apply.
- Out-of-order chunks MUST NOT crash processing.

## Error Handling Contract

- Invalid envelope/payload: reject render path, record diagnostic, continue processing next events.
- Unknown `event_type`: record diagnostic, continue processing next events.
- Backend relay failures SHOULD emit `system.error` when possible.

## Simulator Parity Contract

- Simulated events MUST pass through same validation and routing pipeline as live websocket messages.
- Simulator and live websocket modes MUST not conflict; one authoritative source at a time.

## Compatibility and Versioning

- `schema_version` governs contract evolution.
- Required envelope fields are strict.
- Additional non-breaking payload fields may be accepted for forward compatibility.

## Scope Boundary

- No direct browser-to-Kafka communication.
- No auth protocol definition in this contract.
- No persistent session recovery across browser refresh in v1.
