# How the Telnyx Outbound Hold Agent Works

This cookbook shows how to run an outbound AI phone agent on your own machine. The agent can call another company, navigate an IVR, stop the AI assistant while the call is on hold, keep the phone call connected, and then resume with a live representative using the prior context.

The goal is to give developers a small, runnable reference implementation rather than a full production dialer.

## The Big Picture

```txt
you start an outbound call
-> Telnyx dials the target company
-> when the call is answered, an IVR navigation AI assistant starts
-> the assistant listens to menus and can ask the backend to press DTMF keys
-> when the call reaches hold or a queue, the backend stops the AI assistant
-> the phone call stays connected
-> the backend listens with transcription only
-> when a human representative answers, the backend starts a second AI assistant
-> that second assistant resumes with the original goal and recent context
```

The key idea is that the AI assistant should not spend full assistant runtime on hold music, queue messages, or silence. The call remains connected, but the expensive conversational assistant is paused until the remote side needs interaction again.

## Main Components

| Component | File | Purpose |
| --- | --- | --- |
| FastAPI server | `src/telnyx_hold_agent/server.py` | Exposes local API routes, Telnyx webhook route, and assistant tool endpoints. |
| Orchestrator | `src/telnyx_hold_agent/orchestrator.py` | Owns the call state machine and decides when to start/stop assistants, DTMF, and transcription. |
| Telnyx client | `src/telnyx_hold_agent/telnyx_client.py` | Wraps Telnyx Call Control API calls. |
| State store | `src/telnyx_hold_agent/state.py` | Keeps local in-memory call sessions and recent events. |
| Detectors | `src/telnyx_hold_agent/detectors.py` | Detects hold and representative pickup from transcript text. |
| Prompts | `prompts/assistant-prompts.md` | Contains the two assistant prompts to copy into Telnyx AI Assistants. |
| CLI | `src/telnyx_hold_agent/cli.py` | Provides `hold-agent check`, `hold-agent serve`, and `hold-agent call`. |

## Runtime Flow

1. A developer runs `hold-agent call` or posts to `POST /calls/outbound`.
2. The app creates an in-memory call session with the destination, objective, target company, and optional context.
3. The app sends a Telnyx Call Control Dial command.
4. Telnyx calls back to `POST /webhooks/telnyx` with call lifecycle events.
5. On `call.answered`, the app starts the IVR navigation assistant.
6. The IVR assistant listens to prompts and uses backend tools when it needs an action.
7. If the IVR requires menu input, the assistant calls `/tools/send-dtmf`; the backend sends Telnyx `send_dtmf`.
8. If the call enters a queue or hold period, hold can be detected from:
   - Telnyx `call.hold`.
   - the assistant calling `/tools/hold-detected`.
   - transcript phrases such as "please hold" or "next available representative".
9. Once hold is detected, the backend stops the active assistant with `ai_assistant_stop`.
10. The backend starts transcription-only monitoring with `transcription_start`.
11. While on hold, the backend watches transcript snippets for representative pickup.
12. When a representative is detected, the backend stops hold transcription if needed.
13. The backend starts the representative assistant with the original call context and recent transcript.
14. The representative assistant completes the call objective and the call eventually ends.

## Why There Are Two Assistants

The repo expects two Telnyx AI Assistants because each phase needs different behavior.

### IVR Navigation Assistant

The IVR assistant is active before hold. It should:

- listen to automated menus.
- choose menu options.
- request DTMF through the backend.
- identify when the call reaches hold.
- stop speaking once the backend moves the call into hold monitoring.

It should not directly control the phone call. DTMF stays backend-owned through `/tools/send-dtmf` so menu actions are constrained and auditable.

### Representative Assistant

The representative assistant starts after a human is detected. It should:

- use the original objective and approved context.
- avoid repeating the IVR path unless asked.
- answer the representative's questions.
- complete the assigned business task.
- disclose only information that was supplied for the call.

This separation keeps the prompt for each assistant narrow and makes the hold handoff explicit.

## State Machine

The cookbook uses a simple call state machine:

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

The state machine is implemented in `src/telnyx_hold_agent/orchestrator.py`.

The code also defines additional states such as `hold_candidate`, `task_completed`, and `failed` for future expansion, but the default cookbook flow focuses on the path above.

## API Routes

| Route | Purpose |
| --- | --- |
| `GET /health` | Local health check. |
| `POST /calls/outbound` | Starts a new outbound call. |
| `POST /webhooks/telnyx` | Receives Telnyx call lifecycle and transcription events. |
| `POST /tools/send-dtmf` | Lets the IVR assistant request backend-owned menu key presses. |
| `POST /tools/hold-detected` | Lets the IVR assistant explicitly tell the backend that hold was detected. |
| `GET /sessions` | Lists local in-memory call sessions. |
| `GET /sessions/{session_id}` | Shows one local in-memory call session. |

## Context Handoff

When the representative assistant starts, the backend passes relevant context from the first phase of the call. That context can include:

- session ID.
- original objective.
- target company.
- current call state.
- time on hold.
- user-provided context.
- recent transcript snippets.

This lets the second assistant resume the call without asking the representative to repeat information already collected from the IVR path.

## What Runs on Your Machine

When you run this cookbook locally, your machine runs:

- the FastAPI webhook server.
- the call orchestrator.
- the in-memory session store.
- the detector logic.
- the assistant tool endpoints.

Telnyx runs:

- outbound dialing.
- call media and call control.
- webhook delivery.
- AI assistant execution.
- real-time transcription, depending on your configured transcription engine.

For local testing, Telnyx still needs to reach your machine over public HTTPS. Use a tunnel such as ngrok and set `PUBLIC_BASE_URL` to that tunnel URL.

## What This Is Not

This repo is intentionally not a full production system. Before using it outside a controlled test, add or review:

- Telnyx webhook signature verification with `TELNYX_PUBLIC_KEY`.
- persistent call sessions instead of in-memory state.
- authentication for internal APIs and assistant tool endpoints.
- destination allowlists and rate limits.
- retry and timeout policies for Telnyx commands.
- call transcript, recording, and metadata retention policies.
- compliance review for outbound calling, AI disclosure, recording, and transcription.
- monitoring and alerting for stuck calls, failed commands, and missed representative pickups.

Keep the local demo simple, but treat these production hardening items as required before real customer or regulated workflows.
