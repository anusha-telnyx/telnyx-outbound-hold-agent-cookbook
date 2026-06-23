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
| `demo-script.md` | Short checklist for recording the demo. |

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

## Notes

- Do not treat the fake hotel assistant as part of the core cookbook architecture.
- Use fake guest and reservation data only.
- The hotel assistant should not have the `end-call` tool. The cookbook representative assistant should end the call after both sides say goodbye.
- The demo depends on `PUBLIC_BASE_URL` being reachable by Telnyx so assistant tools and DTMF audio playback work.
