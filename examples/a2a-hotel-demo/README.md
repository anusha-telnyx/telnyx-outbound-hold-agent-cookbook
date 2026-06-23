# A2A Hotel Demo

This is a demo-only example for showing the cookbook working end to end. It is intentionally separate from the core cookbook flow.

The core cookbook still uses two Telnyx AI Assistants:

- IVR navigation assistant.
- Representative interaction assistant.

This demo adds a third Telnyx AI Assistant as the called company. That third assistant behaves like a fake hotel front desk so the cookbook agent can call another AI agent, navigate a menu, wait through hold, and resume with the representative assistant.

## Demo Shape

```txt
cookbook agent calls fake hotel number
-> fake hotel assistant presents reservations menu
-> ivr navigation assistant calls send-dtmf
-> backend sends dtmf and plays a short audible tone
-> fake hotel places call on hold
-> backend stops ivr assistant and monitors hold with transcription
-> fake hotel returns as reservations
-> representative assistant starts with context
-> hotel confirms fake booking
-> both sides say goodbye
-> representative assistant calls end-call
```

## Files

| File | Purpose |
| --- | --- |
| `fake-hotel-assistant-prompt.md` | Prompt for the third, demo-only hotel assistant. |
| `representative-context.json` | Sample context to pass with `hold-agent call`. |
| `tool-config.md` | Tool setup notes for the cookbook assistants and demo target. |

## Setup Checklist

Use this checklist before placing the demo call.

- [ ] Create the IVR navigation assistant.
- [ ] Create the representative assistant.
- [ ] Create the fake hotel assistant.
- [ ] Copy the IVR and representative prompts from `prompts/assistant-prompts.md`.
- [ ] Copy the fake hotel prompt from `fake-hotel-assistant-prompt.md`.
- [ ] Configure the IVR assistant `send_dtmf` tool.
- [ ] Configure the IVR assistant `hold_detected` tool.
- [ ] Configure the representative assistant `end_call` tool.
- [ ] Leave the fake hotel assistant with no tools.
- [ ] Assign the fake hotel assistant to a Telnyx number.
- [ ] Run `ngrok http 8000` or another HTTPS tunnel.
- [ ] Fill `.env` with your Telnyx values.
- [ ] Run `hold-agent check`.
- [ ] Run `hold-agent serve`.
- [ ] Run `hold-agent call` using the fake hotel number.

## Create The Fake Hotel Number

The fake hotel assistant is a third assistant with its own callable Telnyx number. It is separate from the cookbook's IVR navigation assistant and representative assistant.

1. In the Telnyx Mission Control Portal, go to **AI** -> **AI Assistants**.
2. Create a new assistant named something like `Demo Fake Hotel - Willow Creek Reservations`.
3. Copy the prompt from `fake-hotel-assistant-prompt.md`.
4. Set the assistant greeting to:

```text
thank you for calling willow creek hotel. for reservations, press 1. for the front desk, press 2.
```

5. Do not add tools to the fake hotel assistant.
6. Assign the assistant to a Telnyx phone number that can receive calls.
7. Use that phone number as the `--to` number when running `hold-agent call`.

The fake hotel number is the number your cookbook agent calls. Your `TELNYX_FROM_NUMBER` is still your outbound caller ID number.

## Run

Start the cookbook server:

```bash
hold-agent serve
```

In another terminal, call the fake hotel assistant number:

```bash
hold-agent call \
  --to +TEST-COMPANY-PHONE-NUMBER \
  --target-company "Willow Creek Hotel" \
  --objective "book a one-night hotel reservation for one guest" \
  --context-json '{"guest_name":"Alex Morgan","check_in_date":"2026-06-30","nights":1,"room_type":"standard room","budget":"under 250 dollars before taxes","special_requests":"quiet room if available"}'
```

Replace the phone number with your own demo target number if you create a different fake company assistant.

You can also pass the sample context file:

```bash
hold-agent call \
  --to +TEST-COMPANY-PHONE-NUMBER \
  --target-company "Willow Creek Hotel" \
  --objective "book a one-night hotel reservation for one guest" \
  --context-json "$(cat examples/a2a-hotel-demo/representative-context.json)"
```

## Expected Result

A successful run should follow this state path:

```txt
requested
-> dialing
-> ivr_navigation
-> hold_monitoring
-> representative_detected
-> live_conversation
-> call_ended
```

You can inspect local state while the server is running:

```bash
curl http://127.0.0.1:8000/sessions
```

In terminal logs or Telnyx Conversation Insights, expect to see:

- `send_dtmf` called when the IVR assistant selects reservations.
- A short audible DTMF tone when the digit is sent.
- Hold language from the fake hotel assistant.
- The IVR assistant stopping during hold.
- The representative assistant starting after pickup.
- Both sides saying goodbye once.
- `end_call` called by the representative assistant.

## Recording Checklist

For a short demo recording, show:

- The local server running with `hold-agent serve`.
- The outbound call command using the fake hotel number.
- Telnyx Conversation Insights for the call.
- The fake hotel greeting and reservations menu.
- The `send_dtmf` tool call and audible DTMF selection.
- The hold phrase and assistant stop behavior.
- The representative assistant starting with prior context.
- The hotel booking confirmation.
- Both sides saying goodbye once.
- The `end_call` tool call ending the call.

## Notes

- Do not treat the fake hotel assistant as part of the core cookbook architecture.
- Use fake guest and reservation data only.
- The hotel assistant should not have the `end-call` tool. The cookbook representative assistant should end the call after both sides say goodbye.
- The demo depends on `PUBLIC_BASE_URL` being reachable by Telnyx so assistant tools and DTMF audio playback work.
