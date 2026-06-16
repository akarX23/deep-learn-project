"""Test configuration for orchestrator_agent tests.

Stubs missing runtime dependencies so tests can run without kafka-python
installed and without the symbols that master's planner_agent code expects
but doesn't yet export.

Load order (guaranteed by pytest):
  conftest.py → test file imports → test collection
"""

from __future__ import annotations

import sys
import types
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# 1. Stub the kafka package (not installed in dev env)
# ---------------------------------------------------------------------------

def _stub_kafka() -> None:
    if "kafka" not in sys.modules:
        kafka_mod = types.ModuleType("kafka")
        kafka_mod.KafkaProducer = MagicMock  # type: ignore[attr-defined]
        kafka_mod.KafkaConsumer = MagicMock  # type: ignore[attr-defined]
        sys.modules["kafka"] = kafka_mod


_stub_kafka()


# ---------------------------------------------------------------------------
# 2. Add LLMConfig / PlannerConfig / PlannerKafkaConfig to planner_agent.config
#    (master's config.py uses functions, not dataclasses, so these are missing)
# ---------------------------------------------------------------------------

@dataclass
class LLMConfig:
    model: str
    api_base: str | None = None
    api_key: str | None = None
    temperature: float = 0.1
    max_tokens: int = 200


@dataclass
class PlannerKafkaConfig:
    bootstrap_servers: str = "localhost:9092"
    consumer_group_id: str = "planner-agent"
    poll_timeout_ms: int = 1000
    auto_offset_reset: str = "earliest"
    session_timeout_ms: int = 30000
    max_poll_interval_ms: int = 300000


@dataclass
class PlannerConfig:
    llm: LLMConfig = field(default_factory=LLMConfig)
    kafka: PlannerKafkaConfig = field(default_factory=PlannerKafkaConfig)


def _patch_planner_config() -> None:
    import planner_agent.config as _cfg  # noqa: PLC0415

    if not hasattr(_cfg, "LLMConfig"):
        _cfg.LLMConfig = LLMConfig  # type: ignore[attr-defined]
    if not hasattr(_cfg, "PlannerKafkaConfig"):
        _cfg.PlannerKafkaConfig = PlannerKafkaConfig  # type: ignore[attr-defined]
    if not hasattr(_cfg, "PlannerConfig"):
        _cfg.PlannerConfig = PlannerConfig  # type: ignore[attr-defined]
    if not hasattr(_cfg, "get_planner_config"):
        _cfg.get_planner_config = lambda: PlannerConfig()  # type: ignore[attr-defined]


_patch_planner_config()


# ---------------------------------------------------------------------------
# 3. Add call_llm_json to planner_agent.llm_client
#    (classifier.py imports it but master's llm_client.py only has call_llm)
# ---------------------------------------------------------------------------

def _patch_llm_client() -> None:
    import planner_agent.llm_client as _llm  # noqa: PLC0415

    if not hasattr(_llm, "call_llm_json"):
        def _call_llm_json(
            messages: list[dict[str, Any]], config: Any
        ) -> dict[str, Any]:
            raise RuntimeError("call_llm_json stub — patch it in your test")

        _llm.call_llm_json = _call_llm_json  # type: ignore[attr-defined]


_patch_llm_client()
