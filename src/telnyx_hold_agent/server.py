import html
import io
import json
import math
from urllib.parse import parse_qs
import wave

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import Response
from pydantic import ValidationError

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
FAKE_HOTEL_VOICE = "Telnyx.Ultra.0c8ed86e-6c64-40f0-b252-b773911de6bb"

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
    action_url = _public_url(request, "/fake-company/menu")
    body = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<Response>",
        _say("thank you for calling willow creek hotel."),
        f'<Gather action="{html.escape(action_url)}" input="dtmf" numDigits="1" timeout="8" validDigits="12">',
        _say("for reservations, press 1. for the front desk, press 2."),
        "</Gather>",
        "<Redirect>" + html.escape(action_url) + "</Redirect>",
        "</Response>",
    ]
    return Response(content="\n".join(body), media_type="application/xml")


@app.api_route("/fake-company/menu", methods=["GET", "POST"])
async def fake_company_menu(request: Request) -> Response:
    data = await _request_values(request)
    selected = _first_value(data, "Digits", "digits", "dtmf")
    dtmf_url = _public_url(request, "/fake-company/dtmf/1.wav")
    if selected != "1":
        if not selected:
            return _texml_response(
                _say("i did not receive a menu selection. connecting you to reservations."),
                "<Redirect>" + html.escape(_public_url(request, "/fake-company/menu?Digits=1")) + "</Redirect>",
            )
        return _texml_response(
            _say("for reservations, please press 1."),
            f'<Redirect>{html.escape(_public_url(request, "/fake-company/texml"))}</Redirect>',
        )

    return _texml_response(
        f"<Play>{html.escape(dtmf_url)}</Play>",
        _say("reservations. one moment while i connect you."),
        _say("please hold for the next available reservations agent."),
        _say("your call is important to us."),
        '<Pause length="3"/>',
        _say("thanks for holding, this is sarah with willow creek hotel reservations."),
        '<Pause length="5"/>',
        _say("may i have the guest name for the reservation?"),
        '<Pause length="60"/>',
        _say("thanks for calling willow creek hotel. goodbye."),
        "<Hangup/>",
    )


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
    try:
        payload = await request.json()
        tool_request = DtmfToolRequest.model_validate(normalize_tool_payload(payload))
    except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
        return _tool_fallback("send_dtmf", f"invalid tool payload: {exc}")
    if not tool_request.digits:
        return _tool_fallback("send_dtmf", "missing digits")
    call_control_id = tool_request.call_control_id or _latest_active_call_control_id()
    if not call_control_id:
        return _tool_fallback("send_dtmf", "no active call_control_id")
    try:
        response = await orchestrator.send_dtmf(call_control_id, tool_request.digits, tool_request.reason)
    except Exception as exc:
        session = store.get_by_call_control_id(call_control_id)
        if session:
            session.events.append({"tool": "send_dtmf", "accepted": False, "error": str(exc)})
        return _tool_fallback("send_dtmf", str(exc))
    return {"ok": True, "accepted": True, "tool": "send_dtmf", "telnyx_response": response}


@app.post("/tools/hold-detected")
async def hold_detected_tool(request: Request) -> dict[str, object]:
    try:
        payload = await request.json()
        tool_request = HoldDetectedToolRequest.model_validate(normalize_tool_payload(payload))
    except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
        return _tool_fallback("hold_detected", f"invalid tool payload: {exc}")
    call_control_id = tool_request.call_control_id or _latest_active_call_control_id()
    if not call_control_id:
        return _tool_fallback("hold_detected", "no active call_control_id")
    session = store.get_by_call_control_id(call_control_id)
    if not session:
        return _tool_fallback("hold_detected", "unknown call_control_id")
    try:
        await orchestrator.enter_hold(
            session,
            tool_request.reason or "assistant hold-detected tool",
            tool_request.confidence,
        )
    except Exception as exc:
        session.events.append({"tool": "hold_detected", "accepted": False, "error": str(exc)})
        return _tool_fallback("hold_detected", str(exc))
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


def _texml_response(*events: str) -> Response:
    body = ['<?xml version="1.0" encoding="UTF-8"?>', "<Response>", *events, "</Response>"]
    return Response(content="\n".join(body), media_type="application/xml")


def _say(text: str) -> str:
    return f'<Say voice="{html.escape(FAKE_HOTEL_VOICE)}">{html.escape(text)}</Say>'


def _tool_fallback(tool: str, reason: str) -> dict[str, object]:
    return {
        "ok": True,
        "accepted": False,
        "tool": tool,
        "reason": reason,
        "message": "tool request was handled by the demo backend fallback. do not say this out loud. stay silent and continue listening.",
    }


async def _request_values(request: Request) -> dict[str, list[str]]:
    if request.method == "GET":
        return dict(request.query_params.multi_items())

    body = (await request.body()).decode("utf-8")
    if not body:
        return {}

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return {}
        return {key: [str(value)] for key, value in payload.items()}
    return parse_qs(body)


def _first_value(data: dict[str, list[str]], *keys: str) -> str:
    for key in keys:
        value = data.get(key)
        if isinstance(value, list) and value:
            return value[0]
        if isinstance(value, str):
            return value
    return ""


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
