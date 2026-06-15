"""Kafka consumer loop for the Planner Agent service.

Single consumer subscribes to ALL inbound planner topics.  Routing is by
topic name (rule-based):

  init-planner        → agent.run(raw_payload_dict)
  rag-complete        → agent.resume(request_id, payload)
  material-compiled   → agent.resume(request_id, payload)
  quiz-complete       → agent.resume(request_id, payload)

The agent's LangGraph MemorySaver checkpointer restores interrupted state
from the checkpointed thread_id (== request_id), so resume() feeds the
right awaiting node without the worker needing to track pipeline state.

The Kafka producer used by PlannerAgent is created lazily inside the agent
via :func:`planner_agent.kafka.make_producer`; the worker only owns the
inbound consumer.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any

from project.topics import PlannerInboundTopics
from orchestrator_agent.agent import PlannerAgent
from orchestrator_agent.config import PlannerConfig, get_planner_config

logger = logging.getLogger(__name__)

# Completion topics that trigger agent.resume() — topic value → log label.
_RESUME_TOPICS: dict[str, str] = {
    PlannerInboundTopics.RAG_COMPLETE.value: "rag-complete",
    PlannerInboundTopics.MATERIAL_COMPILED.value: "material-compiled",
    PlannerInboundTopics.QUIZ_COMPLETE.value: "quiz-complete",
}


class PlannerWorker:
    """Long-lived Kafka consumer driving the PlannerAgent interrupt/resume pipeline.

    One consumer subscribes to all :class:`~project.topics.PlannerInboundTopics`.
    For init-planner events it starts a new pipeline.  For completion events
    it resumes the paused LangGraph execution identified by the request_id
    embedded in each completion payload.
    """

    def __init__(self, config: PlannerConfig | None = None) -> None:
        self._config = config
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._consumer: Any = None
        self._agent: PlannerAgent | None = None

    @property
    def config(self) -> PlannerConfig:
        if self._config is None:
            self._config = get_planner_config()
        return self._config

    def start(self) -> None:
        """Initialise the inbound consumer and the agent, then start the poll thread.

        The agent uses a lazily-created Kafka producer (via
        :func:`~planner_agent.kafka.make_producer`) so no explicit producer
        wiring is needed here.
        """
        self._consumer = _create_all_topics_consumer(self.config)
        self._agent = PlannerAgent()   # producer created lazily on first publish

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._poll_loop,
            daemon=True,
            name="planner-kafka-worker-loop",
        )
        self._thread.start()
        logger.info("planner_worker_started")

    def stop(self) -> None:
        """Stop the poll loop and close the Kafka consumer."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        if self._consumer is not None:
            try:
                self._consumer.close()
            except Exception:
                pass
        logger.info("planner_worker_stopped")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _poll_loop(self) -> None:
        assert self._consumer is not None
        assert self._agent is not None

        while not self._stop_event.is_set():
            try:
                batches = self._consumer.poll(
                    timeout_ms=self.config.kafka.poll_timeout_ms
                )
                for records in batches.values():
                    for record in records:
                        self._handle_record(record)
            except Exception as exc:
                logger.error("poll_loop_error error=%s", exc)

    def _handle_record(self, record: Any) -> None:
        """Route a consumed Kafka record to agent.run() or agent.resume()."""
        assert self._agent is not None

        topic: str = getattr(record, "topic", "")
        payload: dict[str, Any] = record.value
        request_id: str = str(payload.get("request_id", "unknown"))

        try:
            if topic == PlannerInboundTopics.INIT_PLANNER.value:
                # Pass raw dict — PlannerAgent validates it as PlannerRequestEvent
                # and assigns its own request_id internally.
                logger.info("request_consumed sid=%s", payload.get("sid", "?"))
                self._agent.run(payload)

            elif topic in _RESUME_TOPICS:
                label = _RESUME_TOPICS[topic]
                logger.info(
                    "completion_consumed topic=%s request_id=%s", label, request_id
                )
                self._agent.resume(request_id, payload)

            elif topic == PlannerInboundTopics.USER_CLARIFICATION_RESPONSE.value:
                # Clarification responses are not consumed by the planner in the
                # current design.  The frontend re-sends a new init-planner event
                # with user_level pre-filled after the user answers.
                logger.debug(
                    "user_clarification_response_ignored request_id=%s", request_id
                )

            else:
                logger.warning(
                    "unknown_topic_received topic=%s request_id=%s", topic, request_id
                )

        except Exception as exc:
            logger.error(
                "record_handling_failed topic=%s request_id=%s error=%s",
                topic,
                request_id,
                exc,
            )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def _create_all_topics_consumer(config: PlannerConfig) -> Any:
    """Create a single KafkaConsumer subscribed to all PlannerInboundTopics."""
    try:
        from kafka import KafkaConsumer
    except ImportError as exc:
        raise RuntimeError("kafka-python is required") from exc

    all_inbound = [t.value for t in PlannerInboundTopics]
    return KafkaConsumer(
        *all_inbound,
        bootstrap_servers=config.kafka.bootstrap_servers,
        client_id="planner-agent-consumer",
        group_id=config.kafka.consumer_group_id,
        auto_offset_reset=config.kafka.auto_offset_reset,
        enable_auto_commit=True,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        session_timeout_ms=config.kafka.session_timeout_ms,
        max_poll_interval_ms=config.kafka.max_poll_interval_ms,
    )


def main() -> None:
    """Run the Planner Worker until interrupted."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    worker = PlannerWorker()
    worker.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        worker.stop()


if __name__ == "__main__":
    main()
