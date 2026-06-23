from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from .config import Settings
from .detectors import HoldDetector, RepresentativeDetector
from .models import OutboundCallRequest
from .state import CallSession, CallState, InMemoryCallStore
from .telnyx_client import TelnyxClient


class CallOrchestrator:
    def __init__(self, settings: Settings, store: InMemoryCallStore, telnyx: TelnyxClient) -> None:
        self.settings = settings
        self.store = store
        self.telnyx = telnyx
        self.hold_detector = HoldDetector(settings.hold_confidence_threshold)
        self.representative_detector = RepresentativeDetector(settings.representative_confidence_threshold)

    async def create_outbound_call(self, request: OutboundCallRequest) -> CallSession:
        missing = self.settings.required_missing()
        if missing:
            raise ValueError("Missing required environment variables: " + ", ".join(missing))

        session = CallSession(
            session_id=str(uuid4()),
            to=request.to,
            from_number=self.settings.telnyx_from_number,
            objective=request.objective,
            target_company=request.target_company,
            context=request.context,
        )
        session.transition(CallState.DIALING, "outbound call requested")
        self.store.add(session)

        response = await self.telnyx.dial(
            to=request.to,
            from_number=self.settings.telnyx_from_number,
            connection_id=self.settings.telnyx_connection_id,
            webhook_url=self.settings.webhook_url,
            client_state={"session_id": session.session_id, "stage": "dial"},
        )
        data = response.get("data", {})
        self.store.update_call_ids(
            session.session_id,
            call_control_id=data.get("call_control_id", ""),
            call_leg_id=data.get("call_leg_id", ""),
        )
        session.events.append({"at": datetime.now(UTC).isoformat(), "telnyx_response": data})
        return session

    async def handle_telnyx_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        event_type = extract_event_type(payload)
        call_control_id = extract_call_control_id(payload)
        transcript = extract_transcript(payload)

        if not call_control_id:
            return {"ok": True, "ignored": True, "reason": "no call_control_id", "event_type": event_type}

        session = self.store.get_by_call_control_id(call_control_id)
        if not session:
            return {"ok": True, "ignored": True, "reason": "unknown call_control_id", "event_type": event_type}

        session.events.append({"at": datetime.now(UTC).isoformat(), "event_type": event_type})
        if transcript:
            session.transcript_snippets.append(transcript)

        if event_type == "call.answered":
            await self._start_ivr(session)
        elif event_type == "call.hold":
            await self.enter_hold(session, reason="telnyx call.hold webhook", confidence=1.0)
        elif event_type == "call.unhold":
            await self._representative_detected(session, reason="telnyx call.unhold webhook")
        elif event_type == "call.transcription" and transcript:
            await self._handle_transcript(session, transcript)
        elif event_type == "call.hangup":
            session.active_assistant = None
            session.transcription_active = False
            session.transition(CallState.CALL_ENDED, "telnyx call.hangup webhook")

        return {"ok": True, "event_type": event_type, "state": session.state.value}

    async def send_dtmf(self, call_control_id: str, digits: str, reason: str = "") -> dict[str, Any]:
        session = self.store.get_by_call_control_id(call_control_id)
        if not session:
            raise ValueError("unknown call_control_id")
        response = await self.telnyx.send_dtmf(
            call_control_id=call_control_id,
            digits=digits,
            context={"session_id": session.session_id, "reason": reason, "stage": session.state.value},
        )
        session.events.append({"at": datetime.now(UTC).isoformat(), "dtmf_sent": digits, "reason": reason})
        return response

    async def enter_hold(self, session: CallSession, reason: str, confidence: float) -> None:
        if session.state == CallState.HOLD_MONITORING:
            return
        session.transition(CallState.HOLD_MONITORING, reason, confidence=confidence)
        session.hold_started_at = datetime.now(UTC)

        if session.active_assistant:
            await self.telnyx.stop_ai_assistant(
                call_control_id=session.call_control_id,
                context={"session_id": session.session_id, "stage": "hold_monitoring", "reason": reason},
            )
            session.active_assistant = None

        if not session.transcription_active:
            await self.telnyx.start_transcription(
                call_control_id=session.call_control_id,
                context={"session_id": session.session_id, "stage": "hold_monitoring"},
            )
            session.transcription_active = True

    async def _start_ivr(self, session: CallSession) -> None:
        if session.active_assistant:
            return
        session.transition(CallState.IVR_NAVIGATION, "call answered; starting IVR assistant")
        await self.telnyx.start_ai_assistant(
            call_control_id=session.call_control_id,
            assistant_id=self.settings.telnyx_ivr_assistant_id,
            context=self._assistant_context(session),
            greeting="",
        )
        session.active_assistant = "ivr"

        if self.settings.start_transcription_during_ivr and not session.transcription_active:
            await self.telnyx.start_transcription(
                call_control_id=session.call_control_id,
                context={"session_id": session.session_id, "stage": "ivr_navigation"},
            )
            session.transcription_active = True

    async def _handle_transcript(self, session: CallSession, transcript: str) -> None:
        if session.state == CallState.IVR_NAVIGATION:
            detection = self.hold_detector.evaluate(transcript)
            if detection.matched:
                await self.enter_hold(session, detection.reason, detection.confidence)
        elif session.state == CallState.HOLD_MONITORING:
            detection = self.representative_detector.evaluate(transcript)
            if detection.matched:
                await self._representative_detected(session, detection.reason)

    async def _representative_detected(self, session: CallSession, reason: str) -> None:
        if session.state == CallState.LIVE_CONVERSATION:
            return
        session.transition(CallState.REPRESENTATIVE_DETECTED, reason)

        if session.transcription_active:
            await self.telnyx.stop_transcription(
                call_control_id=session.call_control_id,
                context={"session_id": session.session_id, "stage": "representative_detected"},
            )
            session.transcription_active = False

        await self.telnyx.start_ai_assistant(
            call_control_id=session.call_control_id,
            assistant_id=self.settings.telnyx_representative_assistant_id,
            context=self._assistant_context(session),
            greeting=self._representative_greeting(session),
        )
        session.active_assistant = "representative"
        session.transition(CallState.LIVE_CONVERSATION, "representative assistant started")

    def _representative_greeting(self, session: CallSession) -> str:
        return f"hi, i am calling to {session.objective}."

    def _assistant_context(self, session: CallSession) -> dict[str, Any]:
        hold_seconds = None
        if session.hold_started_at:
            hold_seconds = int((datetime.now(UTC) - session.hold_started_at).total_seconds())
        return {
            "session_id": session.session_id,
            "objective": session.objective,
            "target_company": session.target_company,
            "call_state": session.state.value,
            "time_on_hold_seconds": hold_seconds,
            "user_context": session.context,
            "recent_transcript": session.transcript_snippets[-5:],
        }


def extract_event_type(payload: dict[str, Any]) -> str:
    data = payload.get("data", payload)
    return str(data.get("event_type") or payload.get("event_type") or "")


def extract_call_control_id(payload: dict[str, Any]) -> str:
    data = payload.get("data", payload)
    event_payload = data.get("payload", data)
    return str(
        event_payload.get("call_control_id")
        or data.get("call_control_id")
        or payload.get("call_control_id")
        or ""
    )


def extract_transcript(payload: dict[str, Any]) -> str:
    candidates: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key in {"transcript", "text"} and isinstance(child, str):
                    candidates.append(child)
                else:
                    walk(child)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(payload)
    return next((candidate.strip() for candidate in candidates if candidate.strip()), "")
