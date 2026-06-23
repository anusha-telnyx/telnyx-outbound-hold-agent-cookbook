# Tool Configuration

Configure the cookbook assistants with these tools through the Telnyx AI Assistants portal.

## IVR Navigation Assistant

Use the prompt in `prompts/assistant-prompts.md`.

Tools:

- `send_dtmf`: `POST https://YOUR_PUBLIC_BASE_URL/tools/send-dtmf`
- `hold_detected`: `POST https://YOUR_PUBLIC_BASE_URL/tools/hold-detected`

The `send_dtmf` tool sends the actual keypad digit through Telnyx Call Control and plays a short audible DTMF tone so the demo recording shows the menu selection.

## Representative Assistant

Use the prompt in `prompts/assistant-prompts.md`.

Tool:

- `end_call`: `POST https://YOUR_PUBLIC_BASE_URL/tools/end-call`

The representative assistant should call `end_call` only after the task is complete and both sides have said goodbye.

## Fake Hotel Assistant

Use `fake-hotel-assistant-prompt.md`.

Tools:

- none.

The fake hotel assistant should not hang up the call. It says goodbye once and waits for the cookbook representative assistant to close the call.
