# Data Model: Kafka Backend Integration Service

## Entities

### KafkaConnectionConfig
- Description: Runtime configuration used to create Kafka admin connectivity.
- Fields:
  - bootstrap_servers: str
  - client_id: str
  - security_protocol: str | None
  - sasl_mechanism: str | None
  - sasl_username: str | None
  - sasl_password: str | None
  - ssl_cafile: str | None
  - startup_retry_count: int
  - startup_retry_timeout_seconds: int
- Validation rules:
  - bootstrap_servers must be non-empty.
  - startup_retry_count must be >= 0.
  - startup_retry_timeout_seconds must be >= 1.

### StartupConnectionState
- Description: Service startup state for Kafka admin initialization.
- Fields:
  - attempt: int
  - max_attempts: int
  - status: str (`pending` | `connected` | `failed`)
  - last_error: str | None
- Validation rules:
  - attempt range must remain within [0, max_attempts].

### TopicCreateRequest
- Description: Input payload for topic creation API.
- Fields:
  - topic_name: str
  - num_partitions: int (default 1)
  - replication_factor: int (default 1)
  - config: dict[str, str] | None
- Validation rules:
  - topic_name must be non-empty and Kafka-topic compatible.
  - num_partitions must be >= 1.
  - replication_factor must be >= 1.

### TopicCreateResult
- Description: Output payload for topic creation API.
- Fields:
  - topic_name: str
  - status: str (`created` | `already_exists` | `error`)
  - message: str
  - request_id: str | None
- Validation rules:
  - status must be one of allowed values.
  - message must be non-empty.

### ComposeServiceConfig
- Description: Local docker compose service configuration for developer bootstrap.
- Fields:
  - kafka_service_name: str (default `kafka`)
  - kafka_ui_service_name: str (default `kafka-ui`)
  - kafka_ui_image: str (fixed `provectuslabs/kafka-ui:latest`)
  - kafka_bootstrap_reference: str (default `kafka:9092`)
- Validation rules:
  - kafka_service_name must be non-empty.
  - kafka_ui_service_name must be non-empty.
  - kafka_ui_image must equal `provectuslabs/kafka-ui:latest`.
  - kafka_bootstrap_reference must point to the compose Kafka service.

## Relationships
- One KafkaConnectionConfig governs one service startup lifecycle.
- StartupConnectionState transitions occur during startup attempts using KafkaConnectionConfig values.
- TopicCreateRequest maps to one TopicCreateResult.
- ComposeServiceConfig defines local infrastructure wiring between Kafka and Kafka UI.

## State Transitions

### StartupConnectionState
1. pending -> connected (successful Kafka admin initialization)
2. pending -> pending (retryable failure and attempts remaining)
3. pending -> failed (attempt limit reached)

### TopicCreateResult
1. request_valid -> created (topic created)
2. request_valid -> already_exists (topic previously exists)
3. request_invalid_or_runtime_error -> error

## Derived Fields
- max_attempts = startup_retry_count + 1 (initial attempt plus retries).
- startup timeout budget = max_attempts * startup_retry_timeout_seconds.
