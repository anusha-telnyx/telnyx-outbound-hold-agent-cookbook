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

## Start Here: Get Your Telnyx Values

Use these steps to collect the values for `.env` before running the cookbook.

1. Get `TELNYX_API_KEY`
   - Open the [Telnyx Mission Control Portal](https://portal.telnyx.com/).
   - Go to **API Keys**.
   - Create or copy an API key.
   - Paste it into `.env` as `TELNYX_API_KEY`.

2. Create or find `TELNYX_CONNECTION_ID`
   - In the portal, go to **Voice** -> **Programmable Voice** -> **Voice API Applications**.
   - Create a Voice API / Call Control application, or open an existing one.
   - Set the webhook URL to `https://YOUR_PUBLIC_BASE_URL/webhooks/telnyx`.
   - Copy the application's connection ID.
   - Paste it into `.env` as `TELNYX_CONNECTION_ID`.

3. Choose `TELNYX_FROM_NUMBER`
   - In the portal, go to **Numbers** -> **My Numbers**.
   - Buy or choose a voice-capable Telnyx number.
   - Assign it to the Voice API application from step 2.
   - Copy the number in E.164 format, for example `+15551234567`.
   - Paste it into `.env` as `TELNYX_FROM_NUMBER`.

4. Allow outbound calling
   - In the portal, go to **Voice** -> **Settings** -> **Outbound Voice Profiles**.
   - Open the outbound voice profile associated with your Voice API application.
   - Confirm the destination country you want to call is allowed.
   - For local testing in the US, make sure United States calling is enabled.

5. Create `TELNYX_IVR_ASSISTANT_ID`
   - In the portal, go to **AI** -> **AI Assistants**.
   - Create an assistant for IVR navigation.
   - Copy the IVR navigation prompt from `prompts/assistant-prompts.md`.
   - Add tools for `/tools/send-dtmf` and `/tools/hold-detected`.
   - Copy the assistant ID and paste it into `.env` as `TELNYX_IVR_ASSISTANT_ID`.

6. Create `TELNYX_REPRESENTATIVE_ASSISTANT_ID`
   - In **AI** -> **AI Assistants**, create a second assistant for representative interaction.
   - Copy the representative prompt from `prompts/assistant-prompts.md`.
   - Optionally add the `/tools/end-call` tool so the assistant can end completed calls.
   - Copy the assistant ID and paste it into `.env` as `TELNYX_REPRESENTATIVE_ASSISTANT_ID`.

7. Set `PUBLIC_BASE_URL`
   - Start a tunnel to your local server, for example `ngrok http 8000`.
   - Copy the public HTTPS URL, for example `https://abc123.ngrok-free.app`.
   - Paste it into `.env` as `PUBLIC_BASE_URL`.
   - Update the Voice API application webhook URL from step 2 if the tunnel URL changes.

After these steps, run:

```bash
hold-agent check
```

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

## Demo-Only Example

For a concrete agent-to-agent walkthrough, see [`examples/a2a-hotel-demo`](examples/a2a-hotel-demo). That folder is demo-only and shows how to use a third Telnyx AI Assistant as a fake hotel front desk target.

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

Configure assistant tools with the relevant backend URLs:

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

### End Call

Optionally configure the representative assistant with this tool so it can end the call after the task is complete.

```txt
POST /tools/end-call
```

Body:

```json
{
  "call_control_id": "v3:...",
  "reason": "reservation confirmed and both sides said goodbye",
  "delay_seconds": 3
}
```

`delay_seconds` is optional and defaults to `3`. The delay gives the final goodbye audio time to finish before the backend sends Telnyx `hangup`.

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

The included tests cover detector behavior, webhook payload extraction, assistant tool payload handling, and the demo media endpoints.

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
