# Contract: Backend Service Startup Topic Bootstrap

**Version**: 1.0  
**Date**: 2026-06-12  
**Scope**: Startup behavior of `backend_service` — topic bootstrapping from `project/topics` registry

---

## Startup Sequence Contract

### Preconditions
- `BACKEND_KAFKA_BOOTSTRAP_SERVERS` is set in environment or `.env.local`.
- Kafka cluster is reachable within configured retry limits.

### Startup Steps (ordered)
1. `KafkaSettings.from_env()` — load config.
2. `KafkaAdminService.connect()` — establish admin client connection with retry.
3. `project.topics.get_all_topic_names()` — read required topic list from registry.
4. `KafkaAdminService.bootstrap_topics(topic_names)` — create all topics.
5. `yield` — service becomes ready to handle requests.
6. (on shutdown) `KafkaAdminService.close()` — release admin client.

### Guaranteed Behaviors

| Condition | Outcome |
|---|---|
| Topic does not exist | Created with `num_partitions=1`, `replication_factor=1` |
| Topic already exists | Treated as success (idempotent); logged at DEBUG |
| Transient broker error on one topic | Logged at WARNING; bootstrap continues to remaining topics |
| `project/topics` returns empty list | Bootstrap pass completes immediately with no operations |
| Kafka unreachable within retry limits | Startup fails with `RuntimeError`; service does not become ready |

### Non-Guaranteed / Deferred Behaviors (TODO)

- Per-topic result assertion after creation
- Health check confirming topic is writable after creation
- Advanced per-topic error classification and recovery
- Partition count / replication factor tuning beyond default values

---

## Topic Registry Contract

- **Module**: `project/topics`
- **Aggregator**: `get_all_topic_names() -> list[str]`
- **Topics as of 2026-06-12**: `["rag", "rag-complete"]`
- **Extension**: Add entries to `project/topics` enums; no backend service code changes needed.

## Shared Schema Contract Dependencies

- `project.schemas.StartupTopicBootstrapResult` defines startup bootstrap result structure.
- `project.schemas.RAGRequestEvent` defines Kafka payload validation for `rag` test-event publishing.
- `project.schemas.TestEventPublishResult` and `project.schemas.KafkaPublishMetadata` define normalized API response with optional metadata fields.

## Test-Event API Interaction with Startup

- Test-event route registration depends on runtime route policy (dev/test default enabled, prod opt-in).
- Topic bootstrap remains part of startup lifecycle regardless of test-event route enablement.
- Successful startup bootstrap is a prerequisite for reliable test-event publishing on topic `rag`.

---

## Logging Contract

| Event | Level | Message pattern |
|---|---|---|
| Bootstrap start | INFO | `"Bootstrapping Kafka topics: %s"` (topic list) |
| Topic created | DEBUG | `"Topic created: %s"` |
| Topic already exists | DEBUG | `"Topic already exists: %s"` |
| Topic error | WARNING | `"Failed to bootstrap topic '%s': %s"` |
| Bootstrap summary | INFO | `"Topic bootstrap complete: %d created, %d already existed, %d errors"` |
