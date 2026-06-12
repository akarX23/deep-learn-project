# Research: Backend Kafka Startup Topic Bootstrap

## Decision 1: Topic Name Source
- **Decision**: Read topic names exclusively from `project/topics` module via a new `get_all_topic_names()` aggregator function.
- **Rationale**: `project/topics` is the existing centralized registry; all topic names are already defined there. Adding one aggregator keeps callers ignorant of individual enum classes.
- **Alternatives considered**: Read from environment variables (breaks registry-driven single source of truth), pass topic list as config parameter (pushes registry concern into call site).

## Decision 2: Bootstrap Placement — Method vs. Standalone Function
- **Decision**: Add `bootstrap_topics(topic_names: list[str]) -> StartupTopicBootstrapResult` as a method on `KafkaAdminService`.
- **Rationale**: `KafkaAdminService` already owns the `_client` reference and `create_topic()`. Adding bootstrap as a method keeps Kafka admin operations cohesive and avoids exposing the internal client.
- **Alternatives considered**: Standalone function in `main.py` (scatters Kafka logic across modules), standalone helper module (unnecessary indirection for one call).

## Decision 3: Idempotency Mechanism
- **Decision**: Reuse the existing `create_topic()` method which already catches `TopicAlreadyExistsError` and returns `"already_exists"` — no duplicate-detection logic needed in `bootstrap_topics()`.
- **Rationale**: `TopicAlreadyExistsError` from `kafka-python` is the authoritative signal for topic existence. The existing handler is already correct and tested.
- **Alternatives considered**: Pre-check via `list_topics()` before each create (race-prone and adds a round-trip per topic), suppress all `KafkaError` broadly (masks real errors).

## Decision 4: Non-Fatal Error Handling
- **Decision**: Catch `RuntimeError` raised by `create_topic()` for non-`TopicAlreadyExistsError` Kafka errors; log a WARNING and continue to the next topic.
- **Rationale**: A transient broker error on one topic must not abort the entire bootstrap pass or prevent service startup. Full error-handling policy is a TODO per FR-006.
- **Alternatives considered**: Fail-fast on any topic error (violates FR-008 and spec edge case), silently skip errors (poor observability, violates constitution Principle V).

## Decision 5: Topic Creation Defaults
- **Decision**: Use `num_partitions=1`, `replication_factor=1` as bootstrap defaults.
- **Rationale**: Matches the existing API default in `TopicCreateRequest`. Safe for local and development environments. Production tuning is explicitly out of scope per spec assumptions.
- **Alternatives considered**: Make partition/replication configurable via env vars (adds scope beyond what's requested), use larger defaults (not needed for dev cluster).

## Decision 6: Return Type — StartupTopicBootstrapResult
- **Decision**: `bootstrap_topics()` returns a `StartupTopicBootstrapResult` dataclass with `created`, `already_existed`, and `errors` lists.
- **Rationale**: Gives the caller (lifespan) a structured view of what happened for logging and future use without requiring it to parse log output.
- **Alternatives considered**: Return `None` (caller has no visibility), return raw dict (untyped).

## Decision 7: Logging Approach
- **Decision**: Log topic names before the loop at INFO level; log each outcome (created/already_exists) at DEBUG level; log each error at WARNING level with topic name and error message.
- **Rationale**: Keeps startup output clean at INFO while preserving detailed per-topic visibility at DEBUG. Consistent with existing `logger.info(...)` pattern in `main.py`.
- **Alternatives considered**: Log every topic at INFO (too verbose in production), log only failures (insufficient startup observability per SC-004).
