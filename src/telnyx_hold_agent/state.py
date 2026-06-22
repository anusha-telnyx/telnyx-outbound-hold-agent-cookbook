from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from threading import RLock
from typing import Any


class CallState(StrEnum):
    REQUESTED = "requested"
    DIALING = "dialing"
    ANSWERED = "answered"
    IVR_NAVIGATION = "ivr_navigation"
    HOLD_CANDIDATE = "hold_candidate"
    HOLD_MONITORING = "hold_monitoring"
    REPRESENTATIVE_DETECTED = "representative_detected"
    LIVE_CONVERSATION = "live_conversation"
    TASK_COMPLETED = "task_completed"
    CALL_ENDED = "call_ended"
    FAILED = "failed"


@dataclass
class CallSession:
    session_id: str
    to: str
    from_number: str
    objective: str
    target_company: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    call_control_id: str = ""
    call_leg_id: str = ""
    state: CallState = CallState.REQUESTED
    active_assistant: str | None = None
    transcription_active: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    hold_started_at: datetime | None = None
    transcript_snippets: list[str] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)

    def transition(self, state: CallState, reason: str = "", **metadata: Any) -> None:
        self.state = state
        self.updated_at = datetime.now(UTC)
        self.events.append(
            {
                "at": self.updated_at.isoformat(),
                "state": state.value,
                "reason": reason,
                "metadata": metadata,
            }
        )

    def public_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "to": self.to,
            "from_number": self.from_number,
            "objective": self.objective,
            "target_company": self.target_company,
            "call_control_id": self.call_control_id,
            "call_leg_id": self.call_leg_id,
            "state": self.state.value,
            "active_assistant": self.active_assistant,
            "transcription_active": self.transcription_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "hold_started_at": self.hold_started_at.isoformat() if self.hold_started_at else None,
            "transcript_snippets": self.transcript_snippets[-10:],
            "events": self.events[-50:],
        }


class InMemoryCallStore:
    def __init__(self) -> None:
        self._sessions: dict[str, CallSession] = {}
        self._by_call_control_id: dict[str, str] = {}
        self._lock = RLock()

    def add(self, session: CallSession) -> None:
        with self._lock:
            self._sessions[session.session_id] = session
            if session.call_control_id:
                self._by_call_control_id[session.call_control_id] = session.session_id

    def update_call_ids(self, session_id: str, call_control_id: str = "", call_leg_id: str = "") -> CallSession:
        with self._lock:
            session = self._sessions[session_id]
            if call_control_id:
                session.call_control_id = call_control_id
                self._by_call_control_id[call_control_id] = session_id
            if call_leg_id:
                session.call_leg_id = call_leg_id
            return session

    def get(self, session_id: str) -> CallSession | None:
        with self._lock:
            return self._sessions.get(session_id)

    def get_by_call_control_id(self, call_control_id: str) -> CallSession | None:
        with self._lock:
            session_id = self._by_call_control_id.get(call_control_id)
            if not session_id:
                return None
            return self._sessions.get(session_id)

    def all(self) -> list[CallSession]:
        with self._lock:
            return list(self._sessions.values())

