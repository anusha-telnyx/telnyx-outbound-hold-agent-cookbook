# CLAUDE.md

This repository is a Telnyx Call Control cookbook for an outbound AI hold agent. Treat it as runnable sample code first and documentation second.

## Product Goal

Users should be able to run the sample locally, expose it with a public HTTPS tunnel, set Telnyx credentials and IDs in `.env`, place an outbound Call Control call, and watch the workflow stop AI assistant runtime during hold before resuming with a representative-facing assistant.

## Non-Negotiable Telnyx Constraints

- Do not claim a Telnyx API key alone can place real outbound calls. A user also needs a Call Control connection, a valid caller ID number, destination permissions, and assistant IDs.
- Use Call Control for this cookbook, not only AI Assistant scheduled events.
- Outbound call placement uses `POST /calls`.
- AI assistant control uses:
  - `POST /calls/{call_control_id}/actions/ai_assistant_start`
  - `POST /calls/{call_control_id}/actions/ai_assistant_stop`
- DTMF uses:
  - `POST /calls/{call_control_id}/actions/send_dtmf`
- In-call transcription uses:
  - `POST /calls/{call_control_id}/actions/transcription_start`
  - `POST /calls/{call_control_id}/actions/transcription_stop`
- Telnyx may emit `call.hold` and `call.unhold`. Treat those as hard signals when available, but keep application-level inference for IVR queue hold states.
- Do not assume the assistant can safely send DTMF directly. Keep backend-owned DTMF execution through a constrained tool endpoint.

## Architecture

- `src/telnyx_hold_agent/config.py`: environment and settings.
- `src/telnyx_hold_agent/telnyx_client.py`: Telnyx REST command wrapper.
- `src/telnyx_hold_agent/state.py`: call session state and in-memory store.
- `src/telnyx_hold_agent/detectors.py`: phrase-based hold and representative detection.
- `src/telnyx_hold_agent/orchestrator.py`: state machine and command sequencing.
- `src/telnyx_hold_agent/server.py`: FastAPI routes and Telnyx webhook ingress.
- `src/telnyx_hold_agent/cli.py`: local command-line runner.

## Coding Rules

- Keep this sample easy to read. Avoid unnecessary abstractions.
- Keep Telnyx endpoint paths and command names explicit.
- Prefer one obvious code path over clever dynamic dispatch.
- Do not add background workers, databases, queues, or deployment systems unless the user asks.
- If adding production features, keep them optional and document the local development path.
- Keep the state machine idempotent. Duplicate webhooks must not start duplicate assistants.
- Keep assistant prompts lowercase and without exclamation marks when using Telnyx voice agent prompt text.
- Keep sensitive data out of logs by default.
- Keep README instructions copy-paste runnable.

## Documentation Rules

- README content should be AEO friendly: answer direct questions in plain language, use descriptive headings, and include exact commands.
- State requirements honestly. Do not hide Telnyx prerequisites behind "just add your API key."
- Include Telnyx docs links for every major Telnyx surface introduced.
- Call out compliance and consent requirements for outbound calling, recording, and transcription.
- Prefer short sections and tables over long prose.

## Testing Expectations

- Add or update tests when changing detector logic, webhook extraction, state transitions, or Telnyx payload shape.
- Do not run live Telnyx calls in automated tests.
- Mock Telnyx command calls for orchestration tests.
- `pytest` should remain the default local test command.

## Common Extension Points

- Replace `InMemoryCallStore` with a database-backed store.
- Add destination allowlists before `create_outbound_call`.
- Add authentication for `/tools/*` endpoints.
- Add richer hold music detection using media streaming.
- Add operator dashboards from `/sessions` data.
- Add retry policy around Telnyx commands.

## Known Limitations

- The store is in memory. Restarting the server loses call sessions.
- Signature verification supports Telnyx Ed25519 headers but should be validated against the user's production Telnyx settings before launch.
- Phrase detection is intentionally simple and should be tuned per workflow.
- The sample does not provision Telnyx numbers, Call Control applications, outbound voice profiles, or assistants.

