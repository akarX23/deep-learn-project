# Data Model: Backend Kafka Bootstrap + RAG Test-Event API

## Entities

### StartupTopicBootstrapResult

**Purpose**: Structured record of the startup topic-creation pass returned by `KafkaAdminService.bootstrap_topics()`.

| Field | Type | Description |
|---|---|---|
| `created` | `list[str]` | Topic names successfully created during this startup |
| `already_existed` | `list[str]` | Topic names that already existed (idempotent — not errors) |
| `errors` | `list[tuple[str, str]]` | `(topic_name, error_message)` pairs for topics that encountered non-fatal errors |

**Validation rules**:
- All three lists default to empty; no required fields.
- A result with a non-empty `errors` list is still a valid (partial) outcome — startup continues.

**State transitions**: None — this is a read-only snapshot produced once per startup pass.

---

### RAGRequestEvent (shared schema, reused)

**Purpose**: Canonical Kafka payload contract for publishing test events to topic `rag`.

| Field | Type | Description |
|---|---|---|
| `request_id` | `str` | Correlation identifier (non-empty) |
| `session_ctx` | `dict[str, Any]` | Context map (required, non-null) |
| `user_request` | `str` | End-user request text (non-empty) |
| `file_paths` | `list[str]` | Source files for retrieval (min length 1) |
| `created_at` | `str \| None` | Optional event timestamp |
| `source` | `str \| None` | Optional producer source label |

**Validation rules**:
- `request_id` and `user_request` must be non-empty strings.
- `session_ctx` cannot be null.
- `file_paths` must contain at least one entry.

---

### TestEventPublishResult

**Purpose**: Normalized API response envelope for successful rag test-event publish requests.

| Field | Type | Description |
|---|---|---|
| `request_id` | `str` | Correlation ID copied from published event |
| `topic` | `str` | Kafka topic name (`rag`) |
| `publish_status` | `str` | Publish outcome (`published` for successful sends) |
| `metadata` | `dict[str, int \| None] \| None` | Inline Kafka metadata object with optional `partition`, `offset`, and `timestamp` fields |

**Validation rules**:
- `request_id`, `topic`, and `publish_status` are required.
- `metadata` may be null when broker metadata is unavailable.
- No dedicated schema class is required for metadata; the inline object is sufficient for development-only test flows.

**State transitions**:
- `constructed` -> `validated` -> `returned`

---

### TestEventRoutePolicy

**Purpose**: Runtime route enablement policy for test-event APIs.

| Field | Type | Description |
|---|---|---|
| `environment` | `str` | Current runtime environment (`dev`, `test`, `prod`, etc.) |
| `test_routes_enabled` | `bool` | Effective toggle controlling route registration |

**Validation rules**:
- In `prod`, `test_routes_enabled` defaults to `False` unless explicit opt-in is set.
- In `dev`/`test`, `test_routes_enabled` defaults to `True`.

---

### KafkaProducerHandle

**Purpose**: Single shared producer instance created in the Kafka admin layer and reused by the backend test-events API.

| Field | Type | Description |
|---|---|---|
| `producer` | `object` | Producer instance owned by the Kafka admin layer and exposed for route handlers |

**Validation rules**:
- Only one shared producer exists for the backend service.
- The producer is created in the Kafka admin layer and is not recreated by `main.py`.

---

### TestEventDefaultFactory

**Purpose**: Pure factory functions in `backend_service/app/utils.py`, one per topic, that return a fully initialized, type-safe default instance of each topic's input schema. No validators, no exception handling — type-safe initialized values only. Designed to be used as a convenient starting point for test event publishing.

| Factory | Return Type | Location |
|---------|-------------|----------|
| `default_rag_test_event()` | `RAGRequestEvent` | `backend_service/app/utils.py` |

**`default_rag_test_event()` default field values**:

| Field | Default Value | Notes |
|-------|---------------|-------|
| `request_id` | `f"test-{uuid4().hex}"` | Dynamically generated per call; guarantees uniqueness |
| `session_ctx` | `{"source": "backend-service", "mode": "integration-test"}` | Representative context for local test runs |
| `user_request` | `"Summarize gradient descent for local integration testing."` | Representative domain query |
| `file_paths` | `["rag_agent/tests/inputs/sample.pdf"]` | Points to the existing test fixture |
| `created_at` | `None` | Optional field; omitted by default |
| `source` | `"backend-service"` | Identifies the originating service |

**Constraints**:
- No Pydantic field validators added to the factory itself.
- No exception handling — field values are set to valid defaults so constructor validation passes without error handling.
- Module-level import must have no side effects (no network or Kafka calls).

---

---

### WebSocketEvents

**Purpose**: Shared `project/events.py` module defining WebSocket event-name constants importable by both frontend and backend. Contains names only — no payload models (those stay in `project/schemas.py`).

**Representation**: A `str` Enum so values compare/serialize as plain strings.

| Member | Value | Description |
|---|---|---|
| `STREAM_TOKENS` | `"stream-tokens"` | Server → client token stream event; emission logic implemented later (TODO) |

**Validation rules**:
- Values are stable string literals — renaming a value is a breaking contract change for the frontend.
- Module import must have no side effects (no Socket.IO or network calls) so the frontend toolchain can read names safely.

**Extension rule**: New WebSocket events are added as new enum members here and referenced by both sides.

---

### ConnectionManager

**Purpose**: Minimal in-memory class mapping a `session_id` to its WebSocket connection so Kafka-driven results can be routed to the correct session.

| Field | Type | Description |
|---|---|---|
| `_connections` | `dict[str, Any]` | Maps `session_id` (== Socket.IO `sid`) to the connection/handle used for emitting |

**Methods**:

```
set(session_id: str, connection: Any) -> None   # register/overwrite a session connection
get(session_id: str) -> Any | None              # fetch a session connection (None if absent)
```

**Validation rules**:
- `session_id` IS the Socket.IO-generated `sid`; no separate identifier is introduced.
- Sessions are independent — a single user may own multiple sessions, each stored under its own key.
- No complex exception handling or lifecycle logic in this iteration.

**TODO (deferred)**:
- Removal/cleanup on disconnect.
- Handling `get` for an unknown `session_id` beyond returning `None`.
- Thread/async safety and back-pressure.

---

### SocketModule

**Purpose**: The dedicated `backend_service/app/socket.py` file that owns the Socket.IO server instance, lightweight event listeners, and the emit entry point.

**Key elements**:

| Element | Signature | Description |
|---|---|---|
| `sio` | `socketio.AsyncServer` (ASGI) | Socket.IO server mounted onto the FastAPI app in `main.py` |
| `connect` listener | `async def connect(sid, environ, auth)` | Lightweight; registers `sid` in `ConnectionManager` (implemented later — TODO) |
| `disconnect` listener | `async def disconnect(sid)` | Lightweight stub; cleanup deferred (TODO) |
| `emit_event` | `emit_event(event, payload, session_id) -> None` | Emits `event` with `payload` to the connection identified by `session_id` (== `sid`) |

**Validation rules**:
- `event` values come from `project/events.py` (e.g. `STREAM_TOKENS`).
- `emit_event` routes solely by `session_id`; `user_id` is not used for routing.
- Listeners are lightweight stubs; full behavior (including `stream-tokens` emission flow) is implemented later.

**TODO (deferred)**:
- Full listener bodies and `stream-tokens` emission logic.
- Missing-session handling, authentication, concurrent-emit ordering.

---

### TopicRegistry (read-only, external)

**Purpose**: The `project/topics` module acting as the authoritative list of Kafka topic names required by the system.

**Aggregator function**: `get_all_topic_names() -> list[str]`  
Returns the union of all topic enums registered in `project/topics`.

**Current registry contents** (as of 2026-06-12):

| Enum | Value |
|---|---|
| `PlannerTopics.RAG` | `"rag"` |
| `RAGTopics.RAG_COMPLETE` | `"rag-complete"` |

**Extension rule**: Adding a new topic to `project/topics` automatically includes it in the next startup bootstrap pass — no changes to `backend_service` code are required.

---

### KafkaAdminService (existing, extended)

**New method added**:

```
bootstrap_topics(topic_names: list[str]) -> StartupTopicBootstrapResult
```

**Behavior**:
- Calls `create_topic(name, num_partitions=1, replication_factor=1)` for each topic.
- `"created"` → appends to `result.created`
- `"already_exists"` → appends to `result.already_existed`
- `RuntimeError` → appends `(name, str(exc))` to `result.errors`, logs WARNING, continues

**Precondition**: `_client` must not be `None` (i.e., `connect()` must have been called).

---

## State Diagram: Startup Sequence

```
[Lifespan start]
      │
      ▼
[connect() with retry]
      │ success
      ▼
[get_all_topic_names()]
      │
      ▼
[bootstrap_topics(topic_names)]
      │
      ├─ for each topic
      │       ├─ created         → log DEBUG, add to result.created
      │       ├─ already_exists  → log DEBUG, add to result.already_existed
      │       └─ RuntimeError    → log WARNING, add to result.errors, continue
      │
      ▼
[log bootstrap summary at INFO]
      │
      ├─ if test routes enabled by policy
      │      ▼
      │   [register rag test-event route]
      │
      ▼
[yield — service is ready]
      │
      ▼
[close()]
```
