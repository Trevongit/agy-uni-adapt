"""UATP CLI Tools.

Provides lightweight dogfooding commands such as `uatp-buzz ping`.
Loads seat environment safely without ever logging or exposing secrets.
"""

from __future__ import annotations
import argparse
import asyncio
import os
import signal
import sys
from pathlib import Path
from typing import Optional

from uatp.connectors.buzz import BuzzLocalConnector
from uatp.transport.uds import UDSStreamServer
from uatp.schema import (
    UATPEnvelope,
    UATPMessageType,
    EndpointIdentity,
    ToolCallPayload,
    ToolReturnPayload,
    ErrorPayload
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


async def run_bridge(socket_path: str = "/tmp/uatp-bus.sock", seat: str = "agy-buzz") -> int:
    """Run the UATP IPC Bridge daemon serving requests over Unix Domain Socket."""
    load_seat_env(seat)

    connector = BuzzLocalConnector(
        seat_name=seat,
        relay_url=os.environ.get("BUZZ_RELAY_URL")
    )

    if not connector.is_available():
        sys.stderr.write(f"warning: buzz binary not found at {connector.buzz_binary}. Running in mock mode.\n")

    print(f"[uatp-bridge] Starting UDS bridge at {socket_path} (seat={seat})")

    async def handle_envelope(envelope: UATPEnvelope) -> Optional[UATPEnvelope]:
        # Route tool calls directly to Buzz connector
        if envelope.type == UATPMessageType.TOOL_CALL:
            return await connector.execute_tool_call(envelope)
        elif envelope.type == UATPMessageType.MESSAGE:
            # Echo or acknowledge message
            return UATPEnvelope(
                type=UATPMessageType.TOOL_RETURN,
                source=EndpointIdentity(agent_id="uatp-bridge", runtime="uds-bridge"),
                destination=envelope.source,
                payload=ToolReturnPayload(
                    call_id="ack",
                    name="message_ack",
                    status="success",
                    result={"ack": True, "sender": envelope.source.agent_id}
                ).model_dump()
            )
        elif envelope.type == UATPMessageType.HANDSHAKE:
            return UATPEnvelope(
                type=UATPMessageType.HANDSHAKE,
                source=EndpointIdentity(agent_id="uatp-bridge", runtime="uds-bridge"),
                destination=envelope.source,
                payload={
                    "status": "ready",
                    "protocol_version": "1.0",
                    "seat": seat
                }
            )
        return None

    server = UDSStreamServer(socket_path=socket_path, on_envelope=handle_envelope)
    await server.start()
    print(f"[uatp-bridge] Listening for UATP frames on {socket_path}")

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass

    try:
        await stop_event.wait()
    finally:
        print("[uatp-bridge] Shutting down bridge...")
        await server.stop()
        print("[uatp-bridge] Bridge stopped cleanly.")

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="uatp", description="Universal Agent Translator Protocol CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ping command
    ping_parser = subparsers.add_parser("ping", help="Send a test ping/pong to a Buzz room")
    ping_parser.add_argument("--room", required=True, help="Room/Channel UUID")
    ping_parser.add_argument("--seat", default="agy-buzz", help="Seat ID (default: agy-buzz)")
    ping_parser.add_argument("--message", default=None, help="Custom message content")

    # bridge command
    bridge_parser = subparsers.add_parser("bridge", help="Run UATP IPC Bridge daemon over UDS")
    bridge_parser.add_argument("--socket", default="/tmp/uatp-bus.sock", help="Socket path (default: /tmp/uatp-bus.sock)")
    bridge_parser.add_argument("--seat", default="agy-buzz", help="Seat ID (default: agy-buzz)")

    args = parser.parse_args()

    if args.command == "ping":
        exit_code = asyncio.run(ping_buzz(room=args.room, seat=args.seat, message=args.message))
        sys.exit(exit_code)
    elif args.command == "bridge":
        exit_code = asyncio.run(run_bridge(socket_path=args.socket, seat=args.seat))
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
