"""In-memory per-session conversation store for the Teaching Agent.

The agent maintains its own short-lived chat history keyed by the Socket.IO
session id (``sid``) so follow-up questions are answered with prior turns as
context — without any producer-side (UI / backend / Planner) change. Multi-turn
is therefore on by default; the upstream contract is untouched.

Two bounds keep token usage in check:

- ``max_messages``: keep only the most recent N messages (each user/assistant
  entry counts as one) per session. Default 6 (~3 back-and-forth exchanges).
- ``ttl_seconds``: an idle session — no new turn within this window since its
  last activity — is treated as stale and dropped, so a returning user starts
  fresh. Default 300s (5 minutes).

The store is process-local, simple (a dict + lock), and does not survive a
restart. That is sufficient for short conversational sessions and matches the
worker model: the worker builds exactly one handler, which owns one store and
reuses it across every request it processes.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock


@dataclass
class _Session:
    """A single conversation: ordered turns plus the last-activity timestamp."""

    turns: list[dict]
    last_active: float


class ConversationStore:
    """Bounded, TTL-expiring per-``sid`` chat-history store (thread-safe)."""

    def __init__(
        self,
        max_messages: int = 6,
        ttl_seconds: float = 300.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        # max_messages == 0 disables memory entirely (nothing is ever retained).
        self._max_messages = max(0, max_messages)
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._sessions: dict[str, _Session] = {}
        self._lock = Lock()

    def _is_expired(self, session: _Session, now: float) -> bool:
        return self._ttl_seconds >= 0 and (now - session.last_active) > self._ttl_seconds

    def get_history(self, sid: str) -> list[dict]:
        """Return a copy of the in-window turns for ``sid`` (oldest->newest).

        Returns ``[]`` for an unknown or expired session; an expired session is
        dropped as a side effect. The copy is LLM-message shaped, so it can be
        prepended to the message list directly.
        """
        if not sid:
            return []
        with self._lock:
            session = self._sessions.get(sid)
            if session is None:
                return []
            if self._is_expired(session, self._clock()):
                del self._sessions[sid]
                return []
            return [dict(turn) for turn in session.turns]

    def append_turn(self, sid: str, user_content: str, assistant_content: str) -> None:
        """Append one (user, assistant) exchange for ``sid`` and enforce bounds.

        No-op when ``sid`` or either side is blank. A stale session is reset
        before appending. After appending, the turn list is trimmed to the most
        recent ``max_messages`` entries and ``last_active`` is refreshed.
        """
        if not sid or not user_content or not assistant_content:
            return
        with self._lock:
            now = self._clock()
            session = self._sessions.get(sid)
            if session is None or self._is_expired(session, now):
                session = _Session(turns=[], last_active=now)
                self._sessions[sid] = session
            session.turns.append({"role": "user", "content": user_content})
            session.turns.append({"role": "assistant", "content": assistant_content})
            if self._max_messages and len(session.turns) > self._max_messages:
                session.turns = session.turns[-self._max_messages :]
            elif not self._max_messages:
                session.turns = []
            session.last_active = now

    def clear(self, sid: str | None = None) -> None:
        """Drop one session (``sid``) or all sessions (``sid=None``)."""
        with self._lock:
            if sid is None:
                self._sessions.clear()
            else:
                self._sessions.pop(sid, None)
