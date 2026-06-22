import base64
import json
from typing import Any
from uuid import uuid4

import httpx

from .config import Settings


class TelnyxClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_url = settings.telnyx_api_base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {settings.telnyx_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(f"{self.base_url}{path}", headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    async def dial(self, *, to: str, from_number: str, connection_id: str, webhook_url: str, client_state: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "connection_id": connection_id,
            "from": from_number,
            "to": to,
            "webhook_url": webhook_url,
            "webhook_url_method": "POST",
            "client_state": _encode_client_state(client_state),
            "command_id": str(uuid4()),
        }
        return await self._post("/calls", payload)

    async def start_ai_assistant(
        self,
        *,
        call_control_id: str,
        assistant_id: str,
        context: dict[str, Any],
        greeting: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "assistant": {"id": assistant_id},
            "client_state": _encode_client_state(context),
            "command_id": str(uuid4()),
            "message_history": [
                {
                    "role": "system",
                    "content": "call context: " + json.dumps(context, separators=(",", ":")),
                }
            ],
        }
        if greeting is not None:
            payload["greeting"] = greeting
        return await self._post(f"/calls/{call_control_id}/actions/ai_assistant_start", payload)

    async def stop_ai_assistant(self, *, call_control_id: str, context: dict[str, Any]) -> dict[str, Any]:
        payload = {"client_state": _encode_client_state(context), "command_id": str(uuid4())}
        return await self._post(f"/calls/{call_control_id}/actions/ai_assistant_stop", payload)

    async def send_dtmf(self, *, call_control_id: str, digits: str, context: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "digits": digits,
            "duration_millis": 250,
            "client_state": _encode_client_state(context),
            "command_id": str(uuid4()),
        }
        return await self._post(f"/calls/{call_control_id}/actions/send_dtmf", payload)

    async def start_transcription(self, *, call_control_id: str, context: dict[str, Any]) -> dict[str, Any]:
        config: dict[str, Any] = {
            "transcription_engine": self.settings.transcription_engine,
        }
        if self.settings.transcription_engine == "Deepgram":
            config["transcription_model"] = self.settings.transcription_model
            config["language"] = self.settings.transcription_language
            config["interim_results"] = True
        elif self.settings.transcription_engine == "xAI":
            config["transcription_model"] = self.settings.transcription_model
            config["language"] = self.settings.transcription_language
            config["interim_results"] = True
        else:
            config["language"] = self.settings.transcription_language

        payload = {
            "transcription_engine": self.settings.transcription_engine,
            "transcription_engine_config": config,
            "transcription_tracks": self.settings.transcription_tracks,
            "client_state": _encode_client_state(context),
            "command_id": str(uuid4()),
        }
        return await self._post(f"/calls/{call_control_id}/actions/transcription_start", payload)

    async def stop_transcription(self, *, call_control_id: str, context: dict[str, Any]) -> dict[str, Any]:
        payload = {"client_state": _encode_client_state(context), "command_id": str(uuid4())}
        return await self._post(f"/calls/{call_control_id}/actions/transcription_stop", payload)

    async def hangup(self, *, call_control_id: str, context: dict[str, Any]) -> dict[str, Any]:
        payload = {"client_state": _encode_client_state(context), "command_id": str(uuid4())}
        return await self._post(f"/calls/{call_control_id}/actions/hangup", payload)


def _encode_client_state(value: dict[str, Any]) -> str:
    raw = json.dumps(value, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")

