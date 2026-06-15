"""Socket.IO client for consuming backend event stream with reconnect logic."""

from __future__ import annotations

import asyncio
import logging
import queue
import threading
from datetime import datetime, timezone
from typing import Optional

import socketio

from project.schemas import AgentEvent, ConnectionLifecycleState, EventType

logger = logging.getLogger(__name__)

# Reconnect timing constants
RECONNECT_DELAY_S = 2  # 2 seconds per contract requirement
MAX_RETRIES = 5


class SocketIOClient:
    """Manages Socket.IO connection lifecycle and event ingestion."""

    def __init__(
        self,
        server_url: str,
        event_queue: queue.Queue,
    ):
        """
        Initialize the Socket.IO client.

        Args:
            server_url: Socket.IO server endpoint URL from config
            event_queue: Thread-safe queue shared with the Streamlit script thread.
                Items placed: ("connected", sid), ("state", state, error), ("event", AgentEvent)
        """
        self.server_url = server_url
        self._event_queue = event_queue
        self.sio = socketio.AsyncClient(
            reconnection=True,
            reconnection_attempts=MAX_RETRIES,
            reconnection_delay=RECONNECT_DELAY_S,
            reconnection_delay_max=RECONNECT_DELAY_S,
        )
        self.sid: Optional[str] = None
        self._connect_error_count = 0
        self._running = False

        # Register event handlers
        self.sio.on("connect", self._on_connect)
        self.sio.on("connect_error", self._on_connect_error)
        self.sio.on("disconnect", self._on_disconnect)
        self.sio.on("stream-tokens-skt", self._on_stream_tokens)
        self.sio.on("clarify-user-level-skt", self._on_clarify_user_level)

    def _emit_state(
        self,
        state: ConnectionLifecycleState,
        last_error: str | None = None,
    ) -> None:
        """Put a lifecycle state change into the event queue."""
        self._event_queue.put(("state", state, last_error))

    async def _on_connect(self) -> None:
        """Handle successful connection to Socket.IO server."""
        self.sid = self.sio.sid
        self._connect_error_count = 0
        # Enqueue a dedicated tuple so the Streamlit thread receives sid atomically
        # with the CONNECTED lifecycle state in a single queue item.
        self._event_queue.put(("connected", self.sid))
        logger.info(f"Connected to {self.server_url}, sid={self.sid}")

    async def _on_disconnect(self) -> None:
        """Handle disconnection from Socket.IO server.

        AsyncClient will attempt automatic reconnection per the constructor
        reconnection settings. Emit RECONNECTING so the UI reflects that.
        """
        if self._running:
            self._emit_state(ConnectionLifecycleState.RECONNECTING)
            logger.info("Disconnected from Socket.IO server; AsyncClient will reconnect")
        else:
            self._emit_state(ConnectionLifecycleState.DISCONNECTED)
            logger.info("Disconnected from Socket.IO server")

    async def _on_connect_error(self, data: object) -> None:
        """Handle a failed connection or reconnection attempt.

        Called by AsyncClient for every failed attempt. Once the attempt
        count reaches MAX_RETRIES the lifecycle transitions to FAILED.
        """
        self._connect_error_count += 1
        error_msg = str(data) if data else "connection error"
        if self._connect_error_count >= MAX_RETRIES:
            logger.error(
                f"Connection failed after {self._connect_error_count} attempts: {error_msg}"
            )
            self._emit_state(ConnectionLifecycleState.FAILED, error_msg)
        else:
            logger.warning(
                f"Connection attempt {self._connect_error_count}/{MAX_RETRIES} failed: {error_msg}"
            )
            self._emit_state(ConnectionLifecycleState.RECONNECTING)

    async def _on_stream_tokens(self, data: dict) -> None:
        """Handle stream-tokens-skt event from backend.

        Backend emits StreamTokensEventBody: {from_service, sid, data: {...}}.
        The inner ``data`` dict carries the TeachingTokenPayload fields that
        the router expects (stream_id, sequence, token, is_final).
        """
        try:
            payload = data.get("data", {}) if isinstance(data, dict) else {}
            event = self._build_agent_event(
                event_type=EventType.TEACHING_TOKEN,
                payload=payload,
                source_agent=data.get("from_service", "teaching") if isinstance(data, dict) else "teaching",
            )
            self._event_queue.put(("event", event))
        except Exception as exc:
            logger.error(f"Failed to process stream-tokens event: {exc}", exc_info=True)

    async def _on_clarify_user_level(self, data: dict) -> None:
        """Handle clarify-user-level-skt event from backend.

        Backend emits ClarifyUserLevelEvent: {request_id, user_prompt, sid, reason}.
        Router expects PlannerStatusPayload: {stage, message, progress_percent}.
        Map reason -> message and use a fixed stage to satisfy the contract.
        """
        try:
            raw = data if isinstance(data, dict) else {}
            payload = {
                "stage": "clarify-user-level",
                "message": raw.get("reason") or raw.get("user_prompt") or "Please clarify your level.",
                "progress_percent": None,
            }
            event = self._build_agent_event(
                event_type=EventType.PLANNER_STATUS,
                payload=payload,
                source_agent="planner",
            )
            self._event_queue.put(("event", event))
        except Exception as exc:
            logger.error(f"Failed to process clarify-user-level event: {exc}", exc_info=True)

    def _build_agent_event(
        self,
        event_type: EventType,
        payload: dict,
        source_agent: str,
    ) -> AgentEvent:
        """
        Convert incoming Socket.IO payload into AgentEvent.
        
        Extracts request_id and session_id from payload where available,
        generates event_id and timestamp.
        """
        event_id = payload.get("event_id", f"{self.sid}-{datetime.now(timezone.utc).timestamp()}")
        session_id = payload.get("sid", self.sid or "unknown")
        request_id = payload.get("request_id", None)
        
        return AgentEvent(
            event_id=event_id,
            event_type=event_type,
            source_agent=source_agent,
            session_id=session_id,
            request_id=request_id,
            timestamp=datetime.now(timezone.utc),
            payload=payload,
            schema_version="1.0",
        )

    async def connect(self) -> None:
        """Establish Socket.IO connection."""
        try:
            self._emit_state(ConnectionLifecycleState.CONNECTING)
            await self.sio.connect(self.server_url)
            logger.info(f"Socket.IO connection initiated to {self.server_url}")
        except Exception as exc:
            logger.error(f"Connection failed: {exc}")
            self._emit_state(ConnectionLifecycleState.FAILED, str(exc))
            raise

    async def disconnect(self) -> None:
        """Close Socket.IO connection."""
        try:
            if self.sio.connected:
                await self.sio.disconnect()
            self._emit_state(ConnectionLifecycleState.DISCONNECTED)
            logger.info("Disconnected from Socket.IO")
        except Exception as exc:
            logger.error(f"Error during disconnect: {exc}")

    async def run(self) -> None:
        """Main event loop: connect and wait for events.
        
        Socket.IO event handlers are registered in __init__ and called
        automatically by the AsyncClient. This loop keeps the client
        running until stop() is called. Reconnection is delegated to
        the _on_disconnect handler and AsyncClient's built-in logic.
        """
        self._running = True
        try:
            await self.connect()
            
            # Keep the task alive; handlers fire automatically
            while self._running:
                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            logger.info("Socket.IO run cancelled")
        except Exception as exc:
            logger.error(f"Fatal error in Socket.IO loop: {exc}", exc_info=True)
            self._emit_state(ConnectionLifecycleState.FAILED, str(exc))
        finally:
            await self.disconnect()

    def stop(self) -> None:
        """Request graceful shutdown."""
        self._running = False
        logger.info("Socket.IO client stop requested")


def start_socketio_client(
    server_url: str,
    event_queue: queue.Queue,
) -> SocketIOClient:
    """
    Create a SocketIOClient and start it in a dedicated background thread.

    Safe to call from Streamlit's ScriptRunner thread (no running asyncio loop
    required). The client runs in a daemon thread with its own event loop so it
    is automatically torn down when the process exits.

    Args:
        server_url: Socket.IO server URL (e.g., http://localhost:8001)
        event_queue: Thread-safe queue that receives tuples from the client:
            ("connected", sid)
            ("state", ConnectionLifecycleState, error | None)
            ("event", AgentEvent)

    Returns:
        SocketIOClient instance running in the background thread.
    """
    client = SocketIOClient(server_url, event_queue)

    loop = asyncio.new_event_loop()
    ready = threading.Event()

    def _run_loop() -> None:
        asyncio.set_event_loop(loop)
        ready.set()
        loop.run_forever()

    thread = threading.Thread(target=_run_loop, name="socketio-event-loop", daemon=True)
    thread.start()
    ready.wait()  # ensure loop is running before scheduling coroutine

    asyncio.run_coroutine_threadsafe(client.run(), loop)
    logger.info("Socket.IO background event loop started (thread: %s)", thread.name)
    return client