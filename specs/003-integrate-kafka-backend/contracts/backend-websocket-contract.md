# Contract: Backend Service WebSocket Channel (Socket.IO)

**Version**: 1.0  
**Date**: 2026-06-13  
**Scope**: WebSocket connectivity of `backend_service` — Socket.IO channel, shared event names, connection manager, and per-session emit

---

## Transport Contract

- Transport is Socket.IO via `python-socketio` (ASGI), mounted onto the FastAPI app in `backend_service/app/main.py`.
- The frontend connects as a Socket.IO client; the server assigns a `sid` on connect.
- The application `session_id` IS the Socket.IO-generated `sid` — no separate identifier is introduced.

---

## Shared Event-Name Contract (`project/events.py`)

- Defines a `str` Enum of WebSocket event-name constants importable by both frontend and backend.
- Contains event names only — no payload models (payload shapes live in `project/schemas.py`).
- Module import has no side effects.

| Member | Value | Direction | Notes |
|---|---|---|---|
| `STREAM_TOKENS` | `"stream-tokens"` | Server → client | Emission logic implemented later (TODO) |

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
| Routing key | Always `session_id` (== `sid`); `user_id` is not used for routing |

### Non-Guaranteed / Deferred Behaviors (TODO)

- Full listener bodies and `stream-tokens` emission flow
- Removal/cleanup of sessions on disconnect
- Handling `emit_event` for a missing/unknown `session_id`
- WebSocket authentication/authorization
- Concurrent-emit ordering and back-pressure

---

## Acceptance Mapping

| Spec Requirement | Contract Element |
|---|---|
| FR-020 (Socket.IO mounted) | Transport Contract |
| FR-021 (shared event names) | Shared Event-Name Contract |
| FR-022 (`stream-tokens` defined) | `STREAM_TOKENS` member |
| FR-023, FR-024 (connection manager) | Connection Manager Contract |
| FR-025 (listeners in `socket.py`) | Socket Module Contract |
| FR-026 (`emit_event` signature) | `emit_event` row |
| FR-027 (minimal, deferred edge cases) | Deferred Behaviors (TODO) |
