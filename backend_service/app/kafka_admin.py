from __future__ import annotations

import json
import logging
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import KafkaError, TopicAlreadyExistsError
from kafka import KafkaProducer

from backend_service.app.config import KafkaSettings
from project.schemas import StartupTopicBootstrapResult

logger = logging.getLogger(__name__)


class KafkaAdminService:
    def __init__(self, settings: KafkaSettings) -> None:
        self.settings = settings
        self._client: KafkaAdminClient | None = None
        self._producer: KafkaProducer | None = None

    def connect(self) -> None:
        self._client = KafkaAdminClient(**self.settings.admin_kwargs())
        # Connectivity probe.
        self._client.list_topics()

    def close(self) -> None:
        if self._producer is not None:
            self._producer.close()
        self._producer = None
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

    def bootstrap_topics(self, topic_names: list[str]) -> StartupTopicBootstrapResult:
        """Bootstrap Kafka topics from a list of topic names.

        Creates all topics from the provided list using create_topic() with
        default partition and replication settings. Topic creation is idempotent:
        already-existing topics are not treated as errors.

        Args:
            topic_names: List of topic names to create

        Returns:
            StartupTopicBootstrapResult with created, already_existed, and errors lists

        Note:
            - Transient broker errors are logged but do not abort the bootstrap pass
            - Full error-handling policy (retries, result assertion, health checks)
              is deferred to future iterations (TODO)
        """
        result = StartupTopicBootstrapResult()

        for topic_name in topic_names:
            try:
                status = self.create_topic(
                    topic_name, num_partitions=1, replication_factor=1
                )

                if status == "created":
                    logger.debug("Topic created: %s", topic_name)
                    result.created.append(topic_name)
                elif status == "already_exists":
                    logger.debug("Topic already exists: %s", topic_name)
                    result.already_existed.append(topic_name)

            except RuntimeError as exc:
                logger.warning(
                    "Failed to bootstrap topic '%s': %s", topic_name, str(exc)
                )
                result.errors.append((topic_name, str(exc)))

        return result

    @property
    def producer(self) -> KafkaProducer:
        """Lazy-load and return the shared Kafka producer."""
        if self._producer is None:
            self._producer = KafkaProducer(
                **self.settings.admin_kwargs(),
                value_serializer=lambda value: json.dumps(value).encode("utf-8"),
            )
        return self._producer
