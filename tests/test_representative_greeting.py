import asyncio

from telnyx_hold_agent.config import Settings
from telnyx_hold_agent.orchestrator import CallOrchestrator
from telnyx_hold_agent.state import CallSession, CallState, InMemoryCallStore


class DummyTelnyxClient:
    pass


def test_representative_greeting_restates_objective() -> None:
    orchestrator = CallOrchestrator(Settings(), InMemoryCallStore(), DummyTelnyxClient())  # type: ignore[arg-type]
    session = CallSession(
        session_id="session-1",
        to="+15551234567",
        from_number="+15557654321",
        objective="book a one-night hotel reservation for one guest",
        target_company="Willow Creek Hotel",
    )

    assert (
        orchestrator._representative_greeting(session)
        == "hi, i am calling to book a one-night hotel reservation for one guest."
    )


def test_representative_assistant_starts_before_hold_transcription_cleanup() -> None:
    class RecordingTelnyxClient:
        def __init__(self) -> None:
            self.calls: list[str] = []

        async def start_ai_assistant(self, **kwargs: object) -> dict[str, object]:
            self.calls.append("start_ai_assistant")
            return {}

        async def stop_transcription(self, **kwargs: object) -> dict[str, object]:
            self.calls.append("stop_transcription")
            return {}

    telnyx = RecordingTelnyxClient()
    orchestrator = CallOrchestrator(Settings(), InMemoryCallStore(), telnyx)  # type: ignore[arg-type]
    session = CallSession(
        session_id="session-2",
        to="+15551234567",
        from_number="+15557654321",
        objective="book a one-night hotel reservation for one guest",
        target_company="Willow Creek Hotel",
        call_control_id="call-control-id",
        state=CallState.HOLD_MONITORING,
        transcription_active=True,
    )

    asyncio.run(orchestrator._representative_detected(session, "representative greeting"))

    assert telnyx.calls == ["start_ai_assistant", "stop_transcription"]
    assert session.state == CallState.LIVE_CONVERSATION
    assert session.active_assistant == "representative"
    assert session.transcription_active is False


def test_dtmf_feedback_url_uses_public_media_route() -> None:
    settings = Settings(PUBLIC_BASE_URL="https://example.test")
    orchestrator = CallOrchestrator(settings, InMemoryCallStore(), DummyTelnyxClient())  # type: ignore[arg-type]

    assert orchestrator._dtmf_feedback_url("1") == "https://example.test/media/dtmf/1.wav"
    assert orchestrator._dtmf_feedback_url("#") == "https://example.test/media/dtmf/%23.wav"
