from fastapi.testclient import TestClient

from telnyx_hold_agent import server
from telnyx_hold_agent.state import CallSession, CallState


def test_send_dtmf_tool_returns_controlled_response_on_telnyx_error(monkeypatch) -> None:
    session = CallSession(
        session_id="dtmf-error-session",
        to="+15550000001",
        from_number="+15550000002",
        objective="test",
        call_control_id="dtmf-error-call-control-id",
        state=CallState.IVR_NAVIGATION,
    )
    server.store.add(session)

    async def fail_send_dtmf(call_control_id: str, digits: str, reason: str = "") -> dict[str, object]:
        raise RuntimeError("telnyx rejected send dtmf")

    monkeypatch.setattr(server.orchestrator, "send_dtmf", fail_send_dtmf)

    response = TestClient(server.app).post(
        "/tools/send-dtmf",
        json={
            "call_control_id": "dtmf-error-call-control-id",
            "digits": "1",
            "reason": "select reservations",
        },
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["accepted"] is False


def test_send_dtmf_tool_returns_controlled_response_for_unknown_call() -> None:
    response = TestClient(server.app).post(
        "/tools/send-dtmf",
        json={
            "call_control_id": "unknown-call-control-id",
            "digits": "1",
            "reason": "select reservations",
        },
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["accepted"] is False
    assert "unknown" in response.json()["reason"]


def test_send_dtmf_tool_returns_controlled_response_for_nullable_call_id() -> None:
    response = TestClient(server.app).post(
        "/tools/send-dtmf",
        json={
            "call_control_id": None,
            "digits": "1",
            "reason": "select reservations",
        },
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["accepted"] is False


def test_hold_detected_tool_returns_controlled_response_on_telnyx_error(monkeypatch) -> None:
    session = CallSession(
        session_id="hold-error-session",
        to="+15550000003",
        from_number="+15550000002",
        objective="test",
        call_control_id="hold-error-call-control-id",
        state=CallState.IVR_NAVIGATION,
    )
    server.store.add(session)

    async def fail_enter_hold(session: CallSession, reason: str, confidence: float) -> None:
        raise RuntimeError("telnyx rejected assistant stop")

    monkeypatch.setattr(server.orchestrator, "enter_hold", fail_enter_hold)

    response = TestClient(server.app).post(
        "/tools/hold-detected",
        json={
            "call_control_id": "hold-error-call-control-id",
            "reason": "queue prompt",
            "confidence": 0.9,
        },
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["accepted"] is False


def test_hold_detected_tool_returns_controlled_response_for_unknown_call() -> None:
    response = TestClient(server.app).post(
        "/tools/hold-detected",
        json={
            "call_control_id": "unknown-call-control-id",
            "reason": "queue prompt",
            "confidence": 0.9,
        },
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["accepted"] is False
    assert "unknown" in response.json()["reason"]
