# Data Model: UI Frontend WebSocket Integration

## Entities

### FrontendSession
- Description: Runtime container for one learner-facing UI session.
- Fields:
  - `session_id: str`
  - `active_tab: str` (`chat` | `quiz` | `evaluation`)
  - `connection_state: ConnectionState`
  - `chat_state: ChatStreamState`
  - `quiz_state: QuizState`
  - `evaluation_state: EvaluationState`
  - `planner_status: PlannerStatusState`
  - `diagnostics: list[DiagnosticEvent]`
- Validation rules:
  - `session_id` must be non-empty.
  - `active_tab` must be one of supported tabs.

### ConnectionState
- Description: Transport lifecycle state for websocket connectivity.
- Fields:
  - `state: str` (`connecting` | `connected` | `reconnecting` | `disconnected` | `failed`)
  - `retry_count: int`
  - `last_error: str | None`
  - `last_change_ts: str` (ISO timestamp)
- Validation rules:
  - `retry_count >= 0`
  - `state` must be from allowed enum.

### AgentEvent
- Description: Normalized websocket message envelope.
- Fields:
  - `schema_version: str`
  - `event_id: str`
  - `event_type: str`
  - `source_agent: str`
  - `session_id: str`
  - `request_id: str | None`
  - `timestamp: str` (ISO timestamp)
  - `payload: dict`
  - `status: str | None`
  - `error_message: str | None`
- Validation rules:
  - Required envelope fields cannot be null/empty.
  - Supported `event_type` requires matching payload model.

### ChatStreamState
- Description: Incremental teaching response assembly state.
- Fields:
  - `stream_id: str | None`
  - `rendered_text: str`
  - `last_sequence: int`
  - `is_complete: bool`
- Validation rules:
  - `last_sequence >= -1`
  - Sequence must not regress when applying new chunk.

### TeachingTokenPayload
- Description: Per-chunk teaching stream event payload.
- Fields:
  - `stream_id: str`
  - `sequence: int`
  - `token: str`
  - `is_final: bool`
- Validation rules:
  - `sequence >= 0`
  - `token` may be empty only if `is_final == true`.

### PlannerStatusState
- Description: Planner progress model for status panel.
- Fields:
  - `stage: str`
  - `message: str`
  - `progress_percent: int | None`
  - `updated_at: str`
- Validation rules:
  - `message` non-empty.
  - `progress_percent` in `[0, 100]` when present.

### QuizState
- Description: Quiz lifecycle and current interaction state.
- Fields:
  - `quiz_id: str | None`
  - `phase: str` (`idle` | `started` | `question` | `feedback` | `completed`)
  - `current_question: str | None`
  - `choices: list[str]`
  - `feedback: str | None`
  - `score: float | None`
- Validation rules:
  - `phase` must be from allowed enum.

### EvaluationState
- Description: Most recent and historical evaluation outcomes.
- Fields:
  - `latest_summary: str | None`
  - `strengths: list[str]`
  - `gaps: list[str]`
  - `recommendations: list[str]`
  - `history_count: int`
- Validation rules:
  - `history_count >= 0`

### DiagnosticEvent
- Description: Structured diagnostics for invalid/unknown event handling.
- Fields:
  - `severity: str` (`info` | `warning` | `error`)
  - `reason: str`
  - `event_excerpt: str`
  - `recorded_at: str`
- Validation rules:
  - `reason` non-empty.

### SimulationScenario
- Description: Deterministic event playback definition for local validation.
- Fields:
  - `scenario_id: str`
  - `name: str`
  - `events: list[AgentEvent]`
  - `speed_multiplier: float`
- Validation rules:
  - `events` must be non-empty.
  - `speed_multiplier > 0`.

## Relationships

- One `FrontendSession` has one `ConnectionState`.
- One `FrontendSession` has one each of `ChatStreamState`, `QuizState`, `EvaluationState`, `PlannerStatusState`.
- One `FrontendSession` has many `DiagnosticEvent` entries.
- One `AgentEvent` maps to one concrete payload model based on `event_type`.
- One `SimulationScenario` emits many `AgentEvent` objects through the same pipeline as live input.

## State Transitions

### ConnectionState
1. `connecting` -> `connected` on successful handshake.
2. `connecting` -> `failed` on startup failure.
3. `connected` -> `reconnecting` on unexpected disconnect.
4. `reconnecting` -> `connected` on retry success.
5. `reconnecting` -> `failed` on retry exhaustion.
6. Any state -> `disconnected` on explicit session stop.

### ChatStreamState
1. `stream_id=None` -> active stream on first `teaching.token`.
2. Append ordered token chunks while `is_complete=false`.
3. Mark complete on final chunk or `teaching.complete` event.

### QuizState
1. `idle` -> `started` -> `question` -> `feedback` -> (`question` | `completed`).
2. `completed` is terminal for a quiz instance.
