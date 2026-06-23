from typing import Any

from pydantic import BaseModel, Field


class OutboundCallRequest(BaseModel):
    to: str = Field(description="Destination phone number in E.164 format.")
    objective: str = Field(default="Reach a representative and complete the requested task.")
    target_company: str = Field(default="")
    context: dict[str, Any] = Field(default_factory=dict)


class DtmfToolRequest(BaseModel):
    call_control_id: str | None = ""
    digits: str = ""
    reason: str = ""


class HoldDetectedToolRequest(BaseModel):
    call_control_id: str | None = ""
    reason: str = ""
    confidence: float = 1.0


def normalize_tool_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}

    candidate = payload.get("data", payload)
    if not isinstance(candidate, dict):
        candidate = payload

    arguments = (
        candidate.get("arguments")
        or candidate.get("args")
        or candidate.get("parameters")
        or candidate.get("payload")
    )
    if isinstance(arguments, str):
        try:
            import json

            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            arguments = {}

    if isinstance(arguments, dict):
        normalized = {**candidate, **arguments}
    else:
        normalized = dict(candidate)

    aliases = {
        "callControlId": "call_control_id",
        "call_control_id": "call_control_id",
        "dtmf": "digits",
        "dtmf_digits": "digits",
        "digits": "digits",
    }
    for source, target in aliases.items():
        if source in normalized and target not in normalized:
            normalized[target] = normalized[source]

    return {key: value for key, value in normalized.items() if value is not None}
