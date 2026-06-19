from __future__ import annotations

from datetime import datetime, timezone

from project.schemas import PlannerStatusPayload
from ui_frontend.state import apply_planner_status, create_initial_session


def test_planner_status_reducer_updates_status_fields() -> None:
    session = create_initial_session(session_id="sess-status")
    ts = datetime(2026, 6, 13, 12, 0, 0, tzinfo=timezone.utc)

    updated = apply_planner_status(
        session,
        PlannerStatusPayload(
            stage="dispatch_agents",
            message="Planner dispatched downstream agents",
            progress_percent=55,
        ),
        updated_at=ts,
    )

    assert updated.planner_status.stage == "dispatch_agents"
    assert updated.planner_status.message == "Planner dispatched downstream agents"
    assert updated.planner_status.progress_percent == 55
    assert updated.planner_status.updated_at == ts
