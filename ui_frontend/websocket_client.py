"""WebSocket client for consuming backend event stream with reconnect logic."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Callable, Optional

from project.schemas import AgentEvent, FrontendSession

logger = logging.getLogger(__name__)

# Reconnect timing constants
RECONNECT_DELAY_MS = 2000  # 2 seconds per contract requirement
MAX_RETRIES = 5


class WebSocketClient:
    """Manages WebSocket connection lifecycle and event ingestion."""

    def __init__(
        self,
        websocket_url: str,
        on_event: Callable[[AgentEvent], None],
        on_state_change: Callable[[str], None],
    ):
        """
        Initialize the WebSocket client.

        Args:
            websocket_url: WebSocket endpoint URL from config
            on_event: Callback when a valid event is received
            on_state_change: Callback when connection state changes (for routing to state.py)
        """
        self.websocket_url = websocket_url
        self.on_event = on_event
        self.on_state_change = on_state_change
        self.websocket = None
        self.retry_count = 0
        self._running = False

    async def connect(self) -> None:
        """Establish WebSocket connection."""
        try:
            import websockets

            self.on_state_change("connecting")
            self.websocket = await websockets.connect(self.websocket_url)
            self.on_state_change("connected")
            self.retry_count = 0
            logger.info(f"Connected to {self.websocket_url}")
        except Exception as exc:
            logger.error(f"Connection failed: {exc}")
            self.on_state_change("failed")
            raise

    async def disconnect(self) -> None:
        """Close WebSocket connection."""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        self.on_state_change("disconnected")
        logger.info("Disconnected from WebSocket")

    async def _handle_reconnect(self) -> None:
        """Attempt reconnection with bounded retry."""
        if self.retry_count >= MAX_RETRIES:
            logger.error(f"Max retries ({MAX_RETRIES}) exceeded")
            self.on_state_change("failed")
            return

        self.retry_count += 1
        self.on_state_change("reconnecting")
        logger.info(f"Reconnect attempt {self.retry_count}/{MAX_RETRIES}")

        await asyncio.sleep(RECONNECT_DELAY_MS / 1000.0)

        try:
            await self.connect()
        except Exception as exc:
            logger.error(f"Reconnect attempt {self.retry_count} failed: {exc}")
            if self.retry_count < MAX_RETRIES:
                await self._handle_reconnect()
            else:
                self.on_state_change("failed")

    async def run(self) -> None:
        """Main event loop: connect and consume messages."""
        self._running = True
        try:
            await self.connect()
            while self._running:
                try:
                    message = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=30.0,
                    )
                    await self._process_message(message)
                except asyncio.TimeoutError:
                    logger.debug("WebSocket receive timeout (expected periodic heartbeat)")
                except Exception as exc:
                    logger.error(f"Error receiving message: {exc}")
                    await self._handle_reconnect()
        except asyncio.CancelledError:
            logger.info("WebSocket run cancelled")
        except Exception as exc:
            logger.error(f"Fatal error in WebSocket loop: {exc}")
            self.on_state_change("failed")
        finally:
            await self.disconnect()

    async def _process_message(self, raw_message: str) -> None:
        """Parse and validate incoming WebSocket message."""
        try:
            data = json.loads(raw_message)
            event = AgentEvent(**data)
            self.on_event(event)
        except json.JSONDecodeError as exc:
            logger.error(f"Failed to parse JSON message: {exc}")
        except Exception as exc:
            logger.error(f"Failed to validate event envelope: {exc}")

    def stop(self) -> None:
        """Request graceful shutdown."""
        self._running = False
        logger.info("WebSocket client stop requested")


async def start_websocket_client(
    websocket_url: str,
    on_event: Callable[[AgentEvent], None],
    on_state_change: Callable[[str], None],
) -> WebSocketClient:
    """Factory to create and start a WebSocket client."""
    client = WebSocketClient(websocket_url, on_event, on_state_change)
    asyncio.create_task(client.run())
    return client
