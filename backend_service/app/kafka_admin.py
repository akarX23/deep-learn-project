from __future__ import annotations

from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import KafkaError, TopicAlreadyExistsError

from backend_service.app.config import KafkaSettings


class KafkaAdminService:
    def __init__(self, settings: KafkaSettings) -> None:
        self.settings = settings
        self._client: KafkaAdminClient | None = None

    def connect(self) -> None:
        self._client = KafkaAdminClient(**self.settings.admin_kwargs())
        # Connectivity probe.
        self._client.list_topics()

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
        self._client = None

    def create_topic(
        self,
        topic_name: str,
        num_partitions: int,
        replication_factor: int,
        config: dict[str, str] | None = None,
    ) -> str:
        if self._client is None:
            raise RuntimeError("Kafka admin client is not connected")

        topic = NewTopic(
            name=topic_name,
            num_partitions=num_partitions,
            replication_factor=replication_factor,
            topic_configs=config or {},
        )

        try:
            self._client.create_topics(new_topics=[topic], validate_only=False)
            return "created"
        except TopicAlreadyExistsError:
            return "already_exists"
        except KafkaError as exc:
            raise RuntimeError(f"Kafka topic creation failed: {exc}") from exc
