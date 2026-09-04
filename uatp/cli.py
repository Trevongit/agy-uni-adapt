"""UATP CLI Tools.

Provides lightweight dogfooding commands such as `uatp-buzz ping`.
Loads seat environment safely without ever logging or exposing secrets.
"""

from __future__ import annotations
import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

from uatp.connectors.buzz import BuzzLocalConnector
from uatp.schema import (
    UATPEnvelope,
    UATPMessageType,
    EndpointIdentity,
    ToolCallPayload
)


def load_seat_env(seat: str) -> None:
    """Load seat environment variables from ~/.buzz-dev/agents/<seat>/agent.env safely."""
    env_file = Path.home() / ".buzz-dev" / "agents" / seat / "agent.env"
    if not env_file.is_file():
        # Also check fallback in ~/.buzz/agents/<seat>/agent.env
        env_file = Path.home() / ".buzz" / "agents" / seat / "agent.env"

    if env_file.is_file():
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("\"'")
                if k and k not in os.environ:
                    os.environ[k] = v


async def ping_buzz(room: str, seat: str = "agy-buzz", message: Optional[str] = None) -> int:
    """Send a dogfood PONG/ping message to a Buzz room using UATP BuzzLocalConnector."""
    load_seat_env(seat)

    connector = BuzzLocalConnector(
        seat_name=seat,
        relay_url=os.environ.get("BUZZ_RELAY_URL")
    )

    if not connector.is_available():
        sys.stderr.write(f"error: buzz binary not found at {connector.buzz_binary}\n")
        return 1

    content = message or f"PONG from {seat} (uatp-buzz). Same pubkey. 2-way verified."

    envelope = UATPEnvelope(
        type=UATPMessageType.TOOL_CALL,
        source=EndpointIdentity(agent_id=seat, runtime="antigravity-uatp"),
        payload=ToolCallPayload(
            call_id=f"call_ping_{int(os.times().elapsed * 1000)}",
            name="buzz_messages_send",
            arguments={
                "channel": room,
                "content": content
            }
        ).model_dump()
    )

    return_env = await connector.execute_tool_call(envelope)

    if return_env.type == UATPMessageType.TOOL_RETURN and return_env.payload.get("status") == "success":
        result = return_env.payload.get("result", {})
        event_id = result.get("event_id", "")
        print(f"OK: sent to {room} (event: {event_id[:16]}...)")
        return 0
    else:
        err_detail = return_env.payload.get("detail", "unknown error")
        sys.stderr.write(f"error: failed to send message: {err_detail}\n")
        return 2


def main() -> None:
    parser = argparse.ArgumentParser(prog="uatp-buzz", description="UATP Buzz Dogfood CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ping_parser = subparsers.add_parser("ping", help="Send a test ping/pong to a Buzz room")
    ping_parser.add_argument("--room", required=True, help="Room/Channel UUID")
    ping_parser.add_argument("--seat", default="agy-buzz", help="Seat ID (default: agy-buzz)")
    ping_parser.add_argument("--message", default=None, help="Custom message content")

    args = parser.parse_args()

    if args.command == "ping":
        exit_code = asyncio.run(ping_buzz(room=args.room, seat=args.seat, message=args.message))
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
