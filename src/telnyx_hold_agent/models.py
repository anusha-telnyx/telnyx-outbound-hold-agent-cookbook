from typing import Any

from pydantic import BaseModel, Field


class OutboundCallRequest(BaseModel):
    to: str = Field(description="Destination phone number in E.164 format.")
    objective: str = Field(default="Reach a representative and complete the requested task.")
    target_company: str = Field(default="")
    context: dict[str, Any] = Field(default_factory=dict)


class DtmfToolRequest(BaseModel):
    call_control_id: str
    digits: str
    reason: str = ""


class HoldDetectedToolRequest(BaseModel):
    call_control_id: str
    reason: str = ""
    confidence: float = 1.0

