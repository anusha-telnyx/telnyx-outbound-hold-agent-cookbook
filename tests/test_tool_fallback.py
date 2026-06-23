from telnyx_hold_agent.server import _latest_active_call_control_id, store
from telnyx_hold_agent.state import CallSession, CallState


def test_latest_active_call_control_id_uses_most_recent_active_session() -> None:
    ended = CallSession(
        session_id="ended-session",
        to="+15550000001",
        from_number="+15550000002",
        objective="old call",
        call_control_id="ended-call-control-id",
        state=CallState.CALL_ENDED,
    )
    active = CallSession(
        session_id="active-session",
        to="+15550000003",
        from_number="+15550000002",
        objective="active call",
        call_control_id="active-call-control-id",
        state=CallState.IVR_NAVIGATION,
    )
    store.add(ended)
    store.add(active)

    assert _latest_active_call_control_id() == "active-call-control-id"
