# Telnyx Outbound Hold Agent Cookbook

Build an outbound Telnyx AI voice agent that can call a phone number, navigate IVRs, stop the AI assistant while the call is on hold, monitor the hold with transcription, and restart a representative-facing assistant when a human answers.

This repo is a runnable Python/FastAPI starter for building a hold-aware outbound calling agent on your own machine.

## What You Are Building

The agent keeps the phone call connected while reducing AI assistant runtime during long queue or hold periods.

```txt
outbound call
-> ivr navigation assistant
-> backend-owned dtmf
-> hold detected
-> stop ai assistant
-> transcription-only hold monitoring
-> representative detected
-> representative assistant resumes with context
```

## What This Sample Does

- Places outbound calls with Telnyx Call Control.
- Receives Telnyx call lifecycle webhooks on a local FastAPI server.
- Starts an IVR navigation AI assistant after `call.answered`.
- Lets the assistant request backend-owned DTMF through `/tools/send-dtmf`.
- Moves into hold monitoring from `call.hold`, assistant tool calls, or transcript phrase detection.
- Stops the active AI assistant during hold with `ai_assistant_stop`.
- Starts real-time transcription during hold with `transcription_start`.
- Detects representative pickup from `call.unhold` or transcript phrases.
- Stops hold transcription and starts a representative interaction assistant with call context and a short objective-restating opener.

## How It Works

For a deeper walkthrough of the agent architecture, call flow, state machine, endpoints, context handoff, and production hardening notes, see [`docs/how-it-works.md`](docs/how-it-works.md).

## Quick Answer

Can I run a Telnyx outbound hold agent locally?

Yes. Clone this repo, install the Python dependencies, expose the local FastAPI server with a public HTTPS tunnel such as ngrok, add your Telnyx values to `.env`, then run `hold-agent call --to +15551234567`.

## Requirements

You need:

- Python 3.11 or newer.
- A Telnyx account.
- A Telnyx API key.
- A Telnyx Call Control application or connection ID.
- A Telnyx phone number that can be used as outbound caller ID.
- Outbound voice permissions for the destination country.
- Two Telnyx AI Assistant IDs:
  - one assistant for IVR navigation.
  - one assistant for live representative interaction.
- A public HTTPS URL that forwards to this local server.

An API key authenticates requests to Telnyx, but it is not enough by itself to place a real outbound call. Telnyx also needs a caller ID number, a Call Control connection, assistant IDs, and outbound permissions for the destination country.

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
  --to +16282564467 \
  --target-company "Willow Creek Hotel" \
  --objective "book a one-night hotel reservation for one guest" \
  --context-json '{"guest_name":"Alex Morgan","check_in_date":"2026-06-30","nights":1,"room_type":"standard room","budget":"under 250 dollars before taxes","special_requests":"quiet room if available"}'
```

For a safe end-to-end A2A demo, create a third Telnyx AI Assistant that acts as the called company. In the demo setup used while building this cookbook:

- Fake hotel assistant: `Demo Fake Hotel - Willow Creek Reservations`
- Fake hotel assistant ID: `assistant-0d9b2051-aa12-4b6b-aa8c-7a7999fd4933`
- Fake hotel number: `+16282564467`

That fake hotel assistant is separate from the two cookbook assistants. The cookbook still uses one assistant for IVR navigation and one assistant for the representative/task stage.

The older TeXML fake company endpoint remains available as a low-level smoke test, but it is not the recommended demo for A2A conversation:

```txt
https://YOUR-NGROK-DOMAIN/fake-company/texml
```

The fake hotel answers as Willow Creek Hotel, plays a reservations menu, plays an audible DTMF tone when option 1 is selected, places the caller on hold, then returns with a short representative pickup line and leaves the line open briefly. It is meant to test IVR navigation, hold detection, assistant stop, representative pickup detection, and second-assistant start. It is not meant to simulate a full live booking conversation.

The fake hotel is a TeXML test fixture served by this FastAPI app, not a third Telnyx AI Assistant. It will not appear in the AI Assistants portal. The two AI Assistants in this cookbook are still the outbound IVR navigation assistant and the outbound representative interaction assistant.

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

The default local run path needs only these values:

| Variable | Purpose |
| --- | --- |
| `TELNYX_API_KEY` | Authenticates Telnyx REST API requests. |
| `TELNYX_CONNECTION_ID` | Call Control connection used by the Dial command. |
| `TELNYX_FROM_NUMBER` | Telnyx caller ID number in E.164 format. |
| `TELNYX_IVR_ASSISTANT_ID` | Assistant started after `call.answered`. |
| `TELNYX_REPRESENTATIVE_ASSISTANT_ID` | Assistant started after representative pickup. |
| `PUBLIC_BASE_URL` | Public HTTPS base URL for Telnyx webhooks. |
| `START_TRANSCRIPTION_DURING_IVR` | Defaults to `true` so the backend can detect hold phrases during the demo even if the assistant tool is not configured perfectly. |

## Assistant Setup

Create two Telnyx AI Assistants:

- IVR navigation assistant: use the IVR prompt in `prompts/assistant-prompts.md`.
- Representative assistant: use the representative prompt in `prompts/assistant-prompts.md`.

Add the IVR assistant ID to `TELNYX_IVR_ASSISTANT_ID`.

Add the representative assistant ID to `TELNYX_REPRESENTATIVE_ASSISTANT_ID`.

If you want the IVR assistant to press phone menu options, configure an assistant tool that calls this app's `/tools/send-dtmf` endpoint.

If you want the IVR assistant to explicitly signal hold, configure an assistant tool that calls this app's `/tools/hold-detected` endpoint.

The IVR assistant should call the hold tool silently. It should not say "hold detected" out loud to the remote party.

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

## Assistant Prompts

Copy the assistant prompts from:

```txt
prompts/assistant-prompts.md
```

Use the IVR navigation prompt for `TELNYX_IVR_ASSISTANT_ID` and the representative prompt for `TELNYX_REPRESENTATIVE_ASSISTANT_ID`.

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

Tune the phrase lists and thresholds in `src/telnyx_hold_agent/detectors.py`.

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
