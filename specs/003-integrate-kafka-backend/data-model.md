# Data Model: Backend Kafka Startup Topic Bootstrap

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
      ▼
[yield — service is ready]
      │
      ▼
[close()]
```
