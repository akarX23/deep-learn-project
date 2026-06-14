"""Planner agent worker: consumes init-planner events and runs the workflow."""

from __future__ import annotations

import logging

from planner_agent.agent import PlannerAgent
from planner_agent.kafka import make_consumer
from project.topics import PlannerTopics

logger = logging.getLogger(__name__)


def run_worker() -> None:
    """Consume init-planner events and dispatch each to a PlannerAgent run."""

    consumer = make_consumer(PlannerTopics.INIT_PLANNER.value)
    agent = PlannerAgent()
    logger.info("Planner worker listening on %s", PlannerTopics.INIT_PLANNER.value)
    for message in consumer:
        logger.info("Received init-planner event")
        try:
            agent.run(message.value)
            logger.info("Finished processing init-planner event")
        except Exception as exc:  # noqa: BLE001 - keep the worker alive
            logger.exception("Failed to process planner event: %s", exc)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_worker()
