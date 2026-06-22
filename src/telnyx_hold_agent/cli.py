import argparse
import json
import sys

import httpx
import uvicorn

from .config import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Run and operate the Telnyx outbound hold-agent cookbook.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    subcommands.add_parser("check", help="Validate required environment variables.")
    subcommands.add_parser("serve", help="Start the local FastAPI webhook server.")

    call_parser = subcommands.add_parser("call", help="Ask the local server to place an outbound call.")
    call_parser.add_argument("--to", required=True, help="Destination phone number in E.164 format.")
    call_parser.add_argument("--objective", default="Reach a representative and complete the requested task.")
    call_parser.add_argument("--target-company", default="")
    call_parser.add_argument("--context-json", default="{}", help="Optional JSON object with task context.")
    call_parser.add_argument("--local-url", default="http://127.0.0.1:8000")

    args = parser.parse_args()
    settings = get_settings()

    if args.command == "check":
        missing = settings.required_missing()
        if missing:
            print("Missing required environment variables:")
            for name in missing:
                print(f"- {name}")
            sys.exit(1)
        print("Environment looks ready.")
        print(f"Webhook URL: {settings.webhook_url}")
        return

    if args.command == "serve":
        uvicorn.run("telnyx_hold_agent.server:app", host=settings.app_host, port=settings.app_port, reload=False)
        return

    if args.command == "call":
        try:
            context = json.loads(args.context_json)
        except json.JSONDecodeError as exc:
            print(f"--context-json must be valid JSON: {exc}", file=sys.stderr)
            sys.exit(1)
        response = httpx.post(
            f"{args.local_url.rstrip('/')}/calls/outbound",
            json={
                "to": args.to,
                "objective": args.objective,
                "target_company": args.target_company,
                "context": context,
            },
            timeout=20,
        )
        response.raise_for_status()
        print(json.dumps(response.json(), indent=2))


if __name__ == "__main__":
    main()

