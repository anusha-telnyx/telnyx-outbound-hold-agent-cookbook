# CLAUDE.md

Use this file when working with claude code or another coding assistant inside this repository.

## Project Goal

This project helps a developer run a local telnyx outbound hold agent. The agent places an outbound call, starts an ivr navigation assistant, pauses the ai assistant while the call is on hold, monitors the call with transcription, and starts a representative assistant when a live person joins.

The user should be able to clone this repo, install dependencies, fill in `.env`, expose the server with a public https tunnel, and run one outbound call from their machine.

## What To Preserve

- Keep the sample runnable on a local machine.
- Keep the default setup path simple: `.env`, `hold-agent check`, `hold-agent serve`, `hold-agent call`.
- Keep telnyx call control as the telephony layer.
- Keep dtmf backend-owned through `/tools/send-dtmf`.
- Keep hold detection readable and easy to customize in `src/telnyx_hold_agent/detectors.py`.
- Keep prompts easy to copy from `prompts/assistant-prompts.md`.

## Telnyx Requirements

The user needs a telnyx account with these resources:

- api key.
- call control connection id.
- outbound caller id number.
- ivr navigation assistant id.
- representative assistant id.
- public https webhook url that forwards to this app.

Do not say the api key alone is enough for a real outbound call. The api key authenticates api requests, but telnyx still needs a call control connection, caller id, assistants, and outbound permissions.

## Runtime Flow

```text
create outbound task
-> dial with telnyx call control
-> receive call.answered
-> start ivr assistant
-> send dtmf through backend tool when needed
-> detect hold from call.hold, assistant tool call, or transcription
-> stop assistant
-> start hold transcription
-> detect representative from call.unhold or transcription
-> stop hold transcription
-> start representative assistant with call context
```

## Prompt Rules

Prompts for telnyx voice assistants must be lowercase and must not contain exclamation marks.

When changing prompts, edit:

```text
prompts/assistant-prompts.md
```

## Safe Changes

- Improve setup docs.
- Add tests for detectors or webhook parsing.
- Tune phrase lists in `detectors.py`.
- Add optional production hardening behind clear configuration.
- Add examples that keep the local run path intact.

## Changes To Avoid

- Do not make a cloud deployment mandatory.
- Do not replace call control with scheduled assistant events.
- Do not require a database for the quickstart.
- Do not hide telnyx prerequisites.
- Do not put secrets in source files, logs, prompts, or docs examples.

