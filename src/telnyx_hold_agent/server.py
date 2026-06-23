import html
import io
import json
import math
import wave

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import Response

from .config import Settings, get_settings
from .models import DtmfToolRequest, HoldDetectedToolRequest, OutboundCallRequest, normalize_tool_payload
from .orchestrator import CallOrchestrator
from .security import verify_telnyx_signature
from .state import InMemoryCallStore
from .telnyx_client import TelnyxClient

settings: Settings = get_settings()
store = InMemoryCallStore()
telnyx = TelnyxClient(settings)
orchestrator = CallOrchestrator(settings, store, telnyx)

app = FastAPI(
    title="Telnyx Outbound Hold Agent Cookbook",
    description="Call Control sample that stops an AI assistant during hold and resumes on representative pickup.",
    version="0.1.0",
)


@app.get("/health")
async def health() -> dict[str, object]:
    missing = settings.required_missing()
    return {"ok": not missing, "missing": missing}


@app.api_route("/fake-company/texml", methods=["GET", "POST"])
async def fake_company_texml(request: Request) -> Response:
    dtmf_url = _public_url(request, "/fake-company/dtmf/1.wav")
    script = [
        "thank you for calling willow creek hotel.",
        "for reservations, press 1. for the front desk, press 2.",
        "reservations. one moment while i connect you.",
        "please hold for the next available reservations agent.",
        "your call is important to us.",
        "thanks for holding, this is sarah with willow creek hotel reservations. how can i help you today?",
        "i can help with that. may i have the guest name for the reservation?",
        "thank you. what date would you like to check in?",
        "and how many nights will you be staying?",
        "what room type would you prefer?",
        "i have a standard room available within that budget. would you like me to reserve that?",
        "great. i have reserved a standard room for alex morgan for one night starting june thirtieth, twenty twenty six. the estimated rate is under two hundred fifty dollars before taxes, and i added a quiet room request. is there anything else i can help with?",
        "thank you for calling willow creek hotel. goodbye.",
    ]
    body = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<Response>",
        f"<Say>{html.escape(script[0])}</Say>",
        f"<Say>{html.escape(script[1])}</Say>",
        '<Pause length="2"/>',
        f"<Play>{html.escape(dtmf_url)}</Play>",
        f"<Say>{html.escape(script[2])}</Say>",
        f"<Say>{html.escape(script[3])}</Say>",
        f"<Say>{html.escape(script[4])}</Say>",
        '<Pause length="7"/>',
        f"<Say>{html.escape(script[5])}</Say>",
        '<Pause length="5"/>',
        f"<Say>{html.escape(script[6])}</Say>",
        '<Pause length="7"/>',
        f"<Say>{html.escape(script[7])}</Say>",
        '<Pause length="7"/>',
        f"<Say>{html.escape(script[8])}</Say>",
        '<Pause length="7"/>',
        f"<Say>{html.escape(script[9])}</Say>",
        '<Pause length="7"/>',
        f"<Say>{html.escape(script[10])}</Say>",
        '<Pause length="7"/>',
        f"<Say>{html.escape(script[11])}</Say>",
        '<Pause length="7"/>',
        f"<Say>{html.escape(script[12])}</Say>",
        "</Response>",
    ]
    return Response(content="\n".join(body), media_type="application/xml")


@app.get("/fake-company/dtmf/{digit}.wav")
async def fake_company_dtmf(digit: str) -> Response:
    if digit not in DTMF_FREQUENCIES:
        raise HTTPException(status_code=404, detail="unknown dtmf digit")
    return Response(content=_dtmf_wav(digit), media_type="audio/wav")


@app.post("/calls/outbound")
async def create_outbound_call(request: OutboundCallRequest) -> dict[str, object]:
    try:
        session = await orchestrator.create_outbound_call(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return session.public_dict()


@app.post("/webhooks/telnyx")
async def telnyx_webhook(
    request: Request,
    telnyx_timestamp: str = Header(default=""),
    telnyx_signature_ed25519: str = Header(default=""),
) -> dict[str, object]:
    body = await request.body()
    if not verify_telnyx_signature(settings.telnyx_public_key, telnyx_timestamp, telnyx_signature_ed25519, body):
        raise HTTPException(status_code=401, detail="invalid Telnyx webhook signature")

    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="invalid JSON payload") from exc

    return await orchestrator.handle_telnyx_event(payload)


@app.post("/tools/send-dtmf")
async def send_dtmf_tool(request: Request) -> dict[str, object]:
    tool_request = DtmfToolRequest.model_validate(normalize_tool_payload(await request.json()))
    if not tool_request.digits:
        raise HTTPException(status_code=400, detail="missing digits")
    call_control_id = tool_request.call_control_id or _latest_active_call_control_id()
    if not call_control_id:
        raise HTTPException(status_code=404, detail="no active call_control_id")
    return await orchestrator.send_dtmf(call_control_id, tool_request.digits, tool_request.reason)


@app.post("/tools/hold-detected")
async def hold_detected_tool(request: Request) -> dict[str, object]:
    tool_request = HoldDetectedToolRequest.model_validate(normalize_tool_payload(await request.json()))
    call_control_id = tool_request.call_control_id or _latest_active_call_control_id()
    if not call_control_id:
        raise HTTPException(status_code=404, detail="no active call_control_id")
    session = store.get_by_call_control_id(call_control_id)
    if not session:
        raise HTTPException(status_code=404, detail="unknown call_control_id")
    await orchestrator.enter_hold(
        session,
        tool_request.reason or "assistant hold-detected tool",
        tool_request.confidence,
    )
    return session.public_dict()


@app.get("/sessions")
async def list_sessions() -> list[dict[str, object]]:
    return [session.public_dict() for session in store.all()]


@app.get("/sessions/{session_id}")
async def get_session(session_id: str) -> dict[str, object]:
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="unknown session_id")
    return session.public_dict()


def _latest_active_call_control_id() -> str:
    for session in reversed(store.all()):
        if session.call_control_id and session.state.value not in {"call_ended", "failed"}:
            return session.call_control_id
    return ""


def _public_url(request: Request, path: str) -> str:
    if settings.public_base_url:
        return f"{settings.public_base_url.rstrip('/')}{path}"
    return f"{str(request.base_url).rstrip('/')}{path}"


DTMF_FREQUENCIES = {
    "1": (697, 1209),
    "2": (697, 1336),
    "3": (697, 1477),
    "4": (770, 1209),
    "5": (770, 1336),
    "6": (770, 1477),
    "7": (852, 1209),
    "8": (852, 1336),
    "9": (852, 1477),
    "0": (941, 1336),
    "*": (941, 1209),
    "#": (941, 1477),
}


def _dtmf_wav(digit: str, duration_seconds: float = 0.28, sample_rate: int = 8000) -> bytes:
    low, high = DTMF_FREQUENCIES[digit]
    samples = int(duration_seconds * sample_rate)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = bytearray()
        for index in range(samples):
            t = index / sample_rate
            value = 0.45 * (math.sin(2 * math.pi * low * t) + math.sin(2 * math.pi * high * t))
            frames.extend(int(max(-1.0, min(1.0, value)) * 32767).to_bytes(2, "little", signed=True))
        wav.writeframes(bytes(frames))
    return buffer.getvalue()
