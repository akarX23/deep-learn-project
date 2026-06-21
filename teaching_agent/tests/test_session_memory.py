"""Unit tests for the Teaching Agent's per-session conversation store."""

from __future__ import annotations

from teaching_agent.session_memory import ConversationStore


class _FakeClock:
    """Manually advanced monotonic clock for deterministic TTL tests."""

    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_unknown_sid_returns_empty() -> None:
    store = ConversationStore()
    assert store.get_history("nope") == []


def test_blank_sid_returns_empty_and_is_not_stored() -> None:
    store = ConversationStore()
    store.append_turn("", "q", "a")
    assert store.get_history("") == []


def test_append_and_get_roundtrip_in_order() -> None:
    store = ConversationStore()
    store.append_turn("s1", "What is a loop?", "A loop repeats code.")
    assert store.get_history("s1") == [
        {"role": "user", "content": "What is a loop?"},
        {"role": "assistant", "content": "A loop repeats code."},
    ]


def test_get_history_returns_a_copy() -> None:
    store = ConversationStore()
    store.append_turn("s1", "q", "a")
    history = store.get_history("s1")
    history.append({"role": "user", "content": "mutation"})
    assert len(store.get_history("s1")) == 2  # internal state untouched


def test_blank_content_is_not_stored() -> None:
    store = ConversationStore()
    store.append_turn("s1", "   ".strip(), "a")  # empty user content
    store.append_turn("s1", "q", "")             # empty assistant content
    assert store.get_history("s1") == []


def test_cap_keeps_most_recent_messages() -> None:
    store = ConversationStore(max_messages=4)
    store.append_turn("s1", "q1", "a1")
    store.append_turn("s1", "q2", "a2")
    store.append_turn("s1", "q3", "a3")  # 6 messages -> trimmed to last 4
    assert store.get_history("s1") == [
        {"role": "user", "content": "q2"},
        {"role": "assistant", "content": "a2"},
        {"role": "user", "content": "q3"},
        {"role": "assistant", "content": "a3"},
    ]


def test_default_cap_is_six_messages() -> None:
    store = ConversationStore()  # default max_messages=6
    for i in range(5):  # 10 messages
        store.append_turn("s1", f"q{i}", f"a{i}")
    assert len(store.get_history("s1")) == 6


def test_zero_cap_disables_memory() -> None:
    store = ConversationStore(max_messages=0)
    store.append_turn("s1", "q", "a")
    assert store.get_history("s1") == []


def test_ttl_expires_idle_session() -> None:
    clock = _FakeClock()
    store = ConversationStore(ttl_seconds=300, clock=clock)
    store.append_turn("s1", "q", "a")
    clock.advance(301)  # just past the idle window
    assert store.get_history("s1") == []


def test_active_session_within_ttl_is_kept() -> None:
    clock = _FakeClock()
    store = ConversationStore(ttl_seconds=300, clock=clock)
    store.append_turn("s1", "q", "a")
    clock.advance(299)
    assert len(store.get_history("s1")) == 2


def test_ttl_is_sliding_resets_on_new_turn() -> None:
    clock = _FakeClock()
    store = ConversationStore(ttl_seconds=300, clock=clock)
    store.append_turn("s1", "q1", "a1")
    clock.advance(200)
    store.append_turn("s1", "q2", "a2")  # refreshes last_active
    clock.advance(200)                    # 400s since q1, but only 200s since q2
    assert len(store.get_history("s1")) == 4


def test_stale_session_resets_before_append() -> None:
    clock = _FakeClock()
    store = ConversationStore(ttl_seconds=300, clock=clock)
    store.append_turn("s1", "old-q", "old-a")
    clock.advance(301)
    store.append_turn("s1", "new-q", "new-a")  # old turns dropped first
    assert store.get_history("s1") == [
        {"role": "user", "content": "new-q"},
        {"role": "assistant", "content": "new-a"},
    ]


def test_sessions_are_isolated_by_sid() -> None:
    store = ConversationStore()
    store.append_turn("s1", "q1", "a1")
    store.append_turn("s2", "q2", "a2")
    assert store.get_history("s1") == [
        {"role": "user", "content": "q1"},
        {"role": "assistant", "content": "a1"},
    ]
    assert store.get_history("s2") == [
        {"role": "user", "content": "q2"},
        {"role": "assistant", "content": "a2"},
    ]


def test_clear_one_sid() -> None:
    store = ConversationStore()
    store.append_turn("s1", "q", "a")
    store.append_turn("s2", "q", "a")
    store.clear("s1")
    assert store.get_history("s1") == []
    assert len(store.get_history("s2")) == 2


def test_clear_all() -> None:
    store = ConversationStore()
    store.append_turn("s1", "q", "a")
    store.append_turn("s2", "q", "a")
    store.clear()
    assert store.get_history("s1") == []
    assert store.get_history("s2") == []
