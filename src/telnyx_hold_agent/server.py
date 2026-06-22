import json

from fastapi import FastAPI, Header, HTTPException, Request

from .config import Settings, get_settings
from .models import DtmfToolRequest, HoldDetectedToolRequest, OutboundCallRequest
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
async def send_dtmf_tool(request: DtmfToolRequest) -> dict[str, object]:
    return await orchestrator.send_dtmf(request.call_control_id, request.digits, request.reason)


@app.post("/tools/hold-detected")
async def hold_detected_tool(request: HoldDetectedToolRequest) -> dict[str, object]:
    session = store.get_by_call_control_id(request.call_control_id)
    if not session:
        raise HTTPException(status_code=404, detail="unknown call_control_id")
    await orchestrator.enter_hold(session, request.reason or "assistant hold-detected tool", request.confidence)
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

