from telnyx_hold_agent.config import Settings
from telnyx_hold_agent.orchestrator import CallOrchestrator
from telnyx_hold_agent.state import CallSession, InMemoryCallStore


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
