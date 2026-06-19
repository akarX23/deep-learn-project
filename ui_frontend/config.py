"""Environment-driven configuration for the Streamlit frontend."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class UIConfig:
    websocket_url: str
    backend_url: str
    simulator_enabled: bool = False

    @classmethod
    def from_env(cls) -> "UIConfig":
        websocket_url = os.getenv("UI_WEBSOCKET_URL", "").strip()
        if not websocket_url:
            raise RuntimeError("UI_WEBSOCKET_URL is required")

        backend_url = os.getenv("UI_BACKEND_URL", "").strip()
        if not backend_url:
            raise RuntimeError("UI_BACKEND_URL is required")

        simulator_enabled = os.getenv("UI_SIMULATOR_ENABLED", "false").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

        return cls(
            websocket_url=websocket_url,
            backend_url=backend_url,
            simulator_enabled=simulator_enabled,
        )
