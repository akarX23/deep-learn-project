from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from collections.abc import Callable
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend_service.app.api.test_events import (
    build_test_event_producer,
    router as test_events_router,
)
from backend_service.app.api.topics import router as topics_router
from backend_service.app.config import KafkaSettings
from backend_service.app.kafka_admin import KafkaAdminService
from project.topics import get_all_topic_names

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def create_app(
    settings: KafkaSettings | None = None,
    admin_factory: Callable[[KafkaSettings], KafkaAdminService] = KafkaAdminService,
    test_event_producer_factory: Callable[[KafkaSettings], Any] | None = None,
) -> FastAPI:
    test_event_routes_enabled = _should_enable_test_event_routes(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        resolved_settings = settings or KafkaSettings.from_env()
        app.state.kafka_settings = resolved_settings
        app.state.kafka_admin = admin_factory(resolved_settings)
        app.state.test_event_producer = None
        app.state.test_event_producer_factory = (
            test_event_producer_factory or build_test_event_producer
        )

        max_attempts = resolved_settings.startup_retry_count + 1
        last_error: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info("Kafka admin connect attempt %s/%s", attempt, max_attempts)
                app.state.kafka_admin.connect()
                logger.info("Kafka admin connected")
                break
            except Exception as exc:  # pragma: no cover - defensive branch
                last_error = exc
                if attempt == max_attempts:
                    raise RuntimeError(
                        f"Kafka startup connection failed after {max_attempts} attempts: {last_error}"
                    )
                time.sleep(resolved_settings.startup_retry_timeout_seconds)

        # Bootstrap topics from project registry
        topic_names = get_all_topic_names()
        logger.info("Bootstrapping Kafka topics: %s", topic_names)
        result = app.state.kafka_admin.bootstrap_topics(topic_names)
        logger.info(
            "Topic bootstrap complete: %d created, %d already existed, %d errors",
            len(result.created),
            len(result.already_existed),
            len(result.errors),
        )

        try:
            yield
        finally:
            producer = getattr(app.state, "test_event_producer", None)
            if producer is not None and hasattr(producer, "close"):
                producer.close()
            app.state.kafka_admin.close()

    app = FastAPI(title="Kafka Backend Service", version="0.1.0", lifespan=lifespan)
    app.include_router(topics_router)
    if test_event_routes_enabled:
        app.include_router(test_events_router)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"topic_name": None, "status": "error", "message": str(exc)},
        )

    @app.exception_handler(HTTPException)
    async def handle_http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "topic_name": None,
                "status": "error",
                "message": str(exc.detail),
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled request error", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={
                "topic_name": None,
                "status": "error",
                "message": "Internal server error",
            },
        )

    return app


def _should_enable_test_event_routes(settings: KafkaSettings | None) -> bool:
    if settings is not None:
        return settings.test_event_routes_enabled()

    raw_app_env = os.getenv("APP_ENV", "dev")
    raw_enable = os.getenv("BACKEND_ENABLE_TEST_EVENT_APIS")
    if raw_enable is not None:
        return _parse_bool(raw_enable)
    return raw_app_env.strip().lower() in {"dev", "test"}


def _parse_bool(value: str) -> bool:
    cleaned = value.strip().lower()
    if cleaned in {"1", "true", "yes", "on"}:
        return True
    if cleaned in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError("BACKEND_ENABLE_TEST_EVENT_APIS must be a boolean")


app = create_app()


if __name__ == "__main__":
    uvicorn.run("backend_service.app.main:app", host="0.0.0.0", port=8001, reload=False)
