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
