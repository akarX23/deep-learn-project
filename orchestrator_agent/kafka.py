"""Thin factory helpers for raw kafka-python KafkaProducer instances.

PlannerAgent depends on this module for lazy producer initialisation. Using a
separate module (rather than inlining the factory in agent.py) keeps the agent
testable with a mock producer without touching Kafka connection logic.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def make_producer() -> Any:
    """Create a KafkaProducer reading bootstrap servers from the environment.

    Returns a kafka-python ``KafkaProducer`` configured with:
    * JSON value serialisation
    * UTF-8 key serialisation (accepts ``str`` keys directly)
    * Client ID ``"planner-agent-producer"``

    Raises:
        RuntimeError: if ``kafka-python`` is not installed.
        RuntimeError: if ``KAFKA_BOOTSTRAP_SERVERS`` is not set.
    """
    try:
        from kafka import KafkaProducer
    except ImportError as exc:
        raise RuntimeError(
            "kafka-python is required for the planner agent: pip install kafka-python"
        ) from exc

    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
    if not bootstrap_servers:
        raise RuntimeError(
            "KAFKA_BOOTSTRAP_SERVERS is not set — "
            "set it to a comma-separated list of broker addresses (e.g. localhost:9092)."
        )

    logger.info("make_producer bootstrap_servers=%s", bootstrap_servers)
    return KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        client_id="planner-agent-producer",
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if isinstance(k, str) else k,
    )
