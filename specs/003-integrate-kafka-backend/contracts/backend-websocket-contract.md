# Contract: Backend Service WebSocket Channel (Socket.IO)

**Version**: 1.0  
**Date**: 2026-06-13  
**Scope**: WebSocket connectivity of `backend_service` — Socket.IO channel, shared event contracts (names + bodies), connection manager, per-session emit, and `UserRequest` schema

---

## Transport Contract

- Transport is Socket.IO via `python-socketio` (ASGI), mounted onto the FastAPI app in `backend_service/app/main.py`.
- The frontend connects as a Socket.IO client; the server assigns a `sid` on connect.
- The application `session_id` IS the Socket.IO-generated `sid` — no separate identifier is introduced.

---

## Shared Event Contract (`project/events.py`)

- Defines WebSocket event-name constants (as `str` Enum) and event body schemas importable by both frontend and backend.
- For now includes one event contract: `stream-tokens`.
- Module import has no side effects.

| Member | Value | Direction | Notes |
|---|---|---|---|
| `STREAM_TOKENS` | `"stream-tokens"` | Server → client | Emission logic implemented later (TODO) |

### `stream-tokens` Body Schema

| Field | Type | Required |
|---|---|---|
| `from_service` | `str` | Yes |
| `content` | `str` | Yes |
| `metadata` | `dict[str, Any]` | Yes |

**Validation/handling scope**: No additional custom validation or exception handling in this iteration.

**Stability**: Changing a value is a breaking contract change for the frontend.

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
| `event` argument | Sourced from `project/events.py` constants |
| `payload` for `stream-tokens` | Conforms to `stream-tokens` body schema in `project/events.py` |
| Routing key | Always `session_id` (== `sid`); `user_id` is not used for routing |

### Non-Guaranteed / Deferred Behaviors (TODO)

- Full listener bodies and `stream-tokens` emission flow
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
| `file_data` | `Any` | Yes |
| `sid` | `str` | Yes |

**Validation/handling scope**: No additional custom validation or exception handling in this iteration.

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
