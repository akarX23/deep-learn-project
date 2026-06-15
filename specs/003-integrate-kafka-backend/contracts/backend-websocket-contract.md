# Contract: Backend Service WebSocket Channel + Kafka Consumer (Socket.IO + asyncio)

**Version**: 2.0  
**Date**: 2026-06-14  
**Scope**: WebSocket connectivity of `backend_service` — Socket.IO channel, Kafka consumer integration, shared event contracts (names + bodies), connection manager, per-session emit, and `UserRequest` schema

---

## Transport Contract

- WebSocket transport is Socket.IO via `python-socketio` (ASGI), mounted onto the FastAPI app in `backend_service/app/main.py`.
- The frontend connects as a Socket.IO client; the server assigns a `sid` on connect.
- The application `session_id` IS the Socket.IO-generated `sid` — no separate identifier is introduced.

---

## Kafka Consumer Contract (`backend-service-consumer` asyncio task)

**Lifecycle**:
- Created as an `asyncio` background task during FastAPI lifespan startup via `asyncio.create_task(...)`.
- Task runs before the service yields (service-ready signal) — consumer is polling topics on startup.
- Subscription topics: `clarify-user-level`, `stream-tokens`.
- Consumer group: `backend-service-consumer`.

**Polling Behavior**:

| Topic | Payload Schema | Routing | Emit Event | Emit To |
|---|---|---|---|---|
| `clarify-user-level` | `ClarifyUserLevelEvent` | Extract `sid` field | `clarify-user-level-skt` | Socket.IO session == `sid` |
| `stream-tokens` | `StreamTokensEventBody` | Extract `sid` field | `stream-tokens-skt` | Socket.IO session == `sid` |

**Error Handling**:
- Unknown `sid` or disconnected session: emit is skipped (logging deferred as TODO).
- Payload validation failure: exception caught, logged, polling continues.

---

## Shared Event Contract (`project/events.py`)

- Defines WebSocket event-name constants (as `str` Enum) and imports/re-exports event body schemas from `project/schemas.py`.
- Module import has no side effects.

| Member | Value | Direction | Payload Schema | Notes |
|---|---|---|---|---|
| `STREAM_TOKENS` | `"stream-tokens"` | Kafka topic → backend | `StreamTokensEventBody` | Topics from agents → backend consumer |
| `CLARIFY_USER_LEVEL_SKT` | `"clarify-user-level-skt"` | Server → client (Socket.IO) | `ClarifyUserLevelEvent` | Clarification requests → frontend |
| `STREAM_TOKENS_SKT` | `"stream-tokens-skt"` | Server → client (Socket.IO) | `StreamTokensEventBody` | Token/content streams → frontend |

### `stream-tokens` Kafka Topic Payload Schema (`StreamTokensEventBody`)

| Field | Type | Required | Notes |
|---|---|---|---|
| `from_service` | `str` | Yes | Producing agent identifier (e.g., `rag-agent`) |
| `sid` | `str` | Yes | Target Socket.IO session ID |
| `data` | `dict[str, Any]` | Yes | Agent-specific payload; generic dict for schema flexibility |

**Validation/handling scope**: No additional custom validation or exception handling in this iteration. Backend passes payloads to Socket.IO verbatim.

### `clarify-user-level` Topic Payload Schema (`ClarifyUserLevelEvent` — from planner)

| Field | Type | Required | Notes |
|---|---|---|---|
| `request_id` | `str` | Yes | Correlation identifier |
| `user_prompt` | `str` | Yes | Original user query |
| `sid` | `str` | Yes | Target Socket.IO session ID |
| `reason` | `str` | No | Human-readable clarification reason |

**Stability**: Changing a field is a breaking contract change for the frontend.

---

## Connection Manager Contract (`backend_service/app/connection_manager.py`)

A minimal class mapping `session_id` → connection.

| Method | Signature | Behavior |
|---|---|---|
| `set` | `set(session_id: str, connection: Any) -> None` | Register/overwrite the connection for a session |
| `get` | `get(session_id: str) -> Any \| None` | Return the connection for a session, or `None` if absent |

### Guaranteed Behaviors

| Condition | Outcome |
|---|---|
| New session connects | `set(sid, connection)` stores the mapping |
| Same user opens multiple sessions | Each `session_id` stored independently; no cross-session leakage |
| `get` for a known `session_id` | Returns the stored connection |
| `get` for an unknown `session_id` | Returns `None` |

---

## Socket Module Contract (`backend_service/app/socket.py`)

| Element | Signature | Behavior |
|---|---|---|
| `sio` | `socketio.AsyncServer` (ASGI) | Socket.IO server instance mounted in `main.py` |
| `connect` listener | `async def connect(sid, environ, auth)` | Lightweight; registers `sid` in the connection manager (implemented later — TODO) |
| `disconnect` listener | `async def disconnect(sid)` | Lightweight stub; cleanup deferred (TODO) |
| `emit_event` | `emit_event(event, payload, session_id) -> None` | Emits `event` with `payload` to the connection identified by `session_id` |

### Guaranteed Behaviors

| Condition | Outcome |
|---|---|
| `emit_event(event, payload, session_id)` for a connected session | Payload emitted to that session only |
| `event` argument | Sourced from `project/events.py` constants (e.g., `WebSocketEvents.CLARIFY_USER_LEVEL_SKT`) |
| `payload` for `clarify-user-level-skt` | Conforms to `ClarifyUserLevelEvent` schema |
| `payload` for `stream-tokens-skt` | Conforms to `StreamTokensEventBody` schema |
| Routing key | Always `session_id` (== `sid`); `user_id` is not used for routing |

### Non-Guaranteed / Deferred Behaviors (TODO)

- Full listener bodies and event emission flow
- Removal/cleanup of sessions on disconnect
- Handling `emit_event` for a missing/unknown `session_id`
- WebSocket authentication/authorization
- Concurrent-emit ordering and back-pressure

---

## Shared Backend Schema Contract (`project/schemas.py`)

### `UserRequest`

| Field | Type | Required |
|---|---|---|
| `user_prompt` | `str` | Yes |
| `user_level` | `list[str]` | Yes |
| `sid` | `str` | Yes |

**Validation/handling scope**: No additional custom validation or exception handling in this iteration.

### `StreamTokensEventBody`

Defined in `project/schemas.py`; re-exported from `project/events.py`.

| Field | Type | Required |
|---|---|---|
| `from_service` | `str` | Yes |
| `sid` | `str` | Yes |
| `data` | `dict[str, Any]` | Yes |

---

## Summary: Session 2026-06-14 Contract Updates

- Added socket event name constants `CLARIFY_USER_LEVEL_SKT` and `STREAM_TOKENS_SKT` to `WebSocketEvents`.
- Updated `StreamTokensEventBody` to have `from_service`, `sid`, and `data` (was `from_service`, `content`, `metadata`).
- Added `backend-service-consumer` asyncio task for polling `clarify-user-level` and `stream-tokens` topics.
- Added explicit routing from Kafka topics to Socket.IO events with `ClarifyUserLevelEvent` schema.
- Clarified that `project/events.py` imports/re-exports body schemas from `project/schemas.py` rather than defining them locally.

---

## Acceptance Mapping

| Spec Requirement | Contract Element |
|---|---|
| FR-020 (Socket.IO mounted) | Transport Contract |
| FR-021 (shared event contracts) | Shared Event Contract |
| FR-022 (`stream-tokens` name + body schema) | `STREAM_TOKENS` member + body schema table |
| FR-023, FR-024 (connection manager) | Connection Manager Contract |
| FR-025 (listeners in `socket.py`) | Socket Module Contract |
| FR-026 (`emit_event` signature) | `emit_event` row |
| FR-027 (minimal, deferred edge cases) | Deferred Behaviors (TODO) |
| FR-028 (`UserRequest` schema) | Shared Backend Schema Contract |
| FR-029 (no extra validation/exception handling) | Validation/handling scope notes |
