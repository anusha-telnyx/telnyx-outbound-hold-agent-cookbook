# Telnyx Outbound Hold Agent Cookbook

Build an outbound Telnyx AI voice agent that can call a phone number, navigate IVRs, stop the AI assistant while the call is on hold, monitor the hold with transcription, and restart a representative-facing assistant when a human answers.

This cookbook is a runnable Python/FastAPI starter based on the PRD in `../prd-template.md`.

## What This Sample Does

- Places outbound calls with Telnyx Call Control.
- Receives Telnyx call lifecycle webhooks on a local FastAPI server.
- Starts an IVR navigation AI assistant after `call.answered`.
- Lets the assistant request backend-owned DTMF through `/tools/send-dtmf`.
- Moves into hold monitoring from `call.hold`, assistant tool calls, or transcript phrase detection.
- Stops the active AI assistant during hold with `ai_assistant_stop`.
- Starts real-time transcription during hold with `transcription_start`.
- Detects representative pickup from `call.unhold` or transcript phrases.
- Stops hold transcription and starts a representative interaction assistant with call context.

## Quick Answer

Can I run a Telnyx outbound hold agent locally?

Yes. Start this FastAPI server, expose it with a public tunnel such as ngrok, configure Telnyx Call Control to use that webhook URL, set your Telnyx API key and call settings in `.env`, then run `hold-agent call --to +15551234567`.

## Requirements

You need:

- Python 3.11 or newer.
- A Telnyx account.
- A Telnyx API key.
- A Telnyx Call Control application or connection ID.
- A Telnyx phone number that can be used as outbound caller ID.
- Two Telnyx AI Assistant IDs:
  - one assistant for IVR navigation.
  - one assistant for live representative interaction.
- A public HTTPS URL that forwards to this local server.

An API key alone is not enough to place a real outbound call. Telnyx also needs a caller ID number, a Call Control connection, and outbound permissions for the destination country.

## Install

```bash
cd outbound-hold-agent-cookbook
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Fill in `.env`:

```bash
TELNYX_API_KEY=KEY...
TELNYX_CONNECTION_ID=your-call-control-connection-id
TELNYX_FROM_NUMBER=+15551234567
TELNYX_IVR_ASSISTANT_ID=assistant-...
TELNYX_REPRESENTATIVE_ASSISTANT_ID=assistant-...
PUBLIC_BASE_URL=https://your-public-tunnel.example.com
```

Check config:

```bash
hold-agent check
```

Run the webhook server:

```bash
hold-agent serve
```

In another terminal, place a call:

```bash
hold-agent call \
  --to +15557654321 \
  --target-company "example insurance" \
  --objective "reach eligibility and verify coverage for the provided member"
```

## Local Webhook URL

Telnyx webhooks must reach your machine over HTTPS. For local development, run a tunnel:

```bash
ngrok http 8000
```

Set:

```bash
PUBLIC_BASE_URL=https://YOUR-NGROK-DOMAIN
```

The app will use:

```txt
https://YOUR-NGROK-DOMAIN/webhooks/telnyx
```

## Environment Variables

| Variable | Required | Purpose |
| --- | --- | --- |
| `TELNYX_API_KEY` | Yes | Authenticates Telnyx REST API requests. |
| `TELNYX_CONNECTION_ID` | Yes | Call Control connection used by the Dial command. |
| `TELNYX_FROM_NUMBER` | Yes | Telnyx caller ID number in E.164 format. |
| `TELNYX_IVR_ASSISTANT_ID` | Yes | Assistant started after `call.answered`. |
| `TELNYX_REPRESENTATIVE_ASSISTANT_ID` | Yes | Assistant started after representative pickup. |
| `PUBLIC_BASE_URL` | Yes | Public HTTPS base URL for Telnyx webhooks. |
| `TELNYX_PUBLIC_KEY` | Recommended | Enables Ed25519 webhook signature verification. |
| `START_TRANSCRIPTION_DURING_IVR` | No | Starts transcription during IVR navigation for softer hold detection. Defaults to `false`. |
| `TRANSCRIPTION_ENGINE` | No | STT engine for `transcription_start`. Defaults to `Deepgram`. |
| `TRANSCRIPTION_MODEL` | No | STT model for engines that require a model. Defaults to `deepgram/nova-3`. |
| `TRANSCRIPTION_LANGUAGE` | No | STT language. Defaults to `en`. |
| `TRANSCRIPTION_TRACKS` | No | Telnyx transcription track setting. Defaults to `both`. |

## State Machine

```txt
requested
-> dialing
-> answered
-> ivr_navigation
-> hold_monitoring
-> representative_detected
-> live_conversation
-> call_ended
```

The state machine lives in `src/telnyx_hold_agent/orchestrator.py`.

## Telnyx Webhook Events Used

| Event | Behavior |
| --- | --- |
| `call.answered` | Starts the IVR assistant with `ai_assistant_start`. |
| `call.hold` | Stops the assistant and starts hold monitoring. |
| `call.unhold` | Treats the call as representative-ready and starts the live assistant. |
| `call.transcription` | Runs hold and representative pickup phrase detectors. |
| `call.hangup` | Marks the session ended and clears active resources. |

## Assistant Tool Endpoints

Configure the IVR assistant with backend tools that call these URLs:

### Send DTMF

```txt
POST /tools/send-dtmf
```

Body:

```json
{
  "call_control_id": "v3:...",
  "digits": "1",
  "reason": "select eligibility menu"
}
```

### Signal Hold Detected

```txt
POST /tools/hold-detected
```

Body:

```json
{
  "call_control_id": "v3:...",
  "reason": "ivr said please hold for the next representative",
  "confidence": 0.95
}
```

## Suggested Assistant Instructions

### IVR Navigation Assistant

```txt
you are an ivr navigation assistant for outbound operational calls.

your job is to reach the correct department for the task. listen to automated prompts, choose the most appropriate menu option, and request dtmf through the approved tool when a menu digit is needed.

if the call enters a queue or hold period, do not continue speaking. call the hold-detected tool and wait for the system to resume the next stage.
```

### Representative Assistant

```txt
you are now speaking with a live representative.

use the provided call context and do not repeat ivr navigation details unless asked. stay silent through greetings or hold-return scripts unless the representative asks a question or requests the reason for the call.

complete the assigned business task accurately, disclose only approved information, and end the call professionally when the task is complete.
```

## Customizing Hold Detection

Edit:

```txt
src/telnyx_hold_agent/detectors.py
```

Start with phrase-based detection, then add richer signals as needed:

- repeated queue announcements.
- non-speech windows.
- media streaming analysis.
- known IVR paths.
- destination-specific phrase lists.

## Testing

```bash
pytest
```

The included tests cover the detector behavior and basic Telnyx webhook payload extraction.

## Troubleshooting

### `hold-agent check` says variables are missing

Copy `.env.example` to `.env` and fill in every required value.

### Telnyx never calls my webhook

Confirm `PUBLIC_BASE_URL` is public HTTPS, your tunnel is running, and `/health` is reachable from the internet.

### The call fails immediately

Check that:

- `TELNYX_CONNECTION_ID` is a Call Control connection.
- `TELNYX_FROM_NUMBER` belongs to the Telnyx account or is allowed as caller ID.
- the outbound voice profile allows the destination country.
- the destination is in E.164 format.

### The assistant starts but cannot press menu keys

The assistant should not directly send DTMF. Configure a tool that calls `/tools/send-dtmf`, and let the backend send Telnyx `send_dtmf`.

### The representative assistant starts too early

Tune `HOLD_CONFIDENCE_THRESHOLD`, `REPRESENTATIVE_CONFIDENCE_THRESHOLD`, and the phrase lists in `detectors.py`.

## Production Notes

Before using this outside a controlled test:

- verify Telnyx webhook signatures with `TELNYX_PUBLIC_KEY`.
- persist call sessions in a database instead of in memory.
- add authentication to tool endpoints.
- add destination allowlists and rate limits.
- review outbound calling, recording, and transcription compliance.
- decide transcript and recording retention policy.
- add alerting for stuck calls and command failures.

## Telnyx Docs

- Telnyx docs overview: https://developers.telnyx.com/docs/overview
- Voice API docs: https://telnyx.com/llms/calling/voice-api.txt
- AI Assistants docs: https://telnyx.com/llms/ai/assistants.txt
- STT docs: https://telnyx.com/llms/voice/stt.txt
