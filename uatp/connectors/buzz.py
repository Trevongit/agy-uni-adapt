"""Buzz Local Connector for UATP.

Integrates with local buzz-cli against a live Buzz community, invoking
the CLI (`buzz --format compact`) and handling event translation across
NIP-33/34 and UATP envelopes.
"""

from __future__ import annotations
import asyncio
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from uatp.schema import (
    UATPEnvelope,
    UATPMessageType,
    EndpointIdentity,
    ToolReturnPayload,
    ErrorPayload
)


class BuzzLocalConnector:
    """Handles interaction with local buzz installations and workspaces."""

    def __init__(
        self,
        buzz_binary: Optional[str] = None,
        relay_url: Optional[str] = None,
        seat_name: str = "default",
        nest_dir: Optional[str] = None
    ):
        self.buzz_binary = buzz_binary or shutil.which("buzz") or str(Path.home() / ".local/bin/buzz")
        self.relay_url = relay_url
        self.seat_name = seat_name
        self.nest_dir = Path(nest_dir or os.path.expanduser("~/.buzz"))
        self.endpoint = EndpointIdentity(
            agent_id=f"buzz-{seat_name}",
            runtime="buzz-connector"
        )

    def is_available(self) -> bool:
        """Check if buzz executable exists on host."""
        return os.path.isfile(self.buzz_binary) and os.access(self.buzz_binary, os.X_OK)

    async def execute_tool_call(self, tool_envelope: UATPEnvelope) -> UATPEnvelope:
        """Execute a UATP tool call payload against Buzz CLI."""
        payload = tool_envelope.payload
        call_id = payload.get("call_id", "")
        tool_name = payload.get("name", "")
        args = payload.get("arguments", {})

        cmd = [self.buzz_binary, "--format", "compact"]
        if self.relay_url:
            cmd.extend(["--relay", self.relay_url])

        if tool_name == "buzz_messages_send":
            channel = args.get("channel")
            content = args.get("content", "")
            if not channel:
                return self._build_error_envelope(
                    call_id=call_id,
                    tool_name=tool_name,
                    category="user_error",
                    code=1,
                    detail="Missing required argument 'channel'"
                )
            cmd.extend(["messages", "send", "--channel", channel, "--content", content])
            for mention in args.get("mentions", []):
                cmd.extend(["--mention", mention])

        elif tool_name == "buzz_messages_get":
            channel = args.get("channel")
            limit = args.get("limit", 20)
            if not channel:
                return self._build_error_envelope(
                    call_id=call_id,
                    tool_name=tool_name,
                    category="user_error",
                    code=1,
                    detail="Missing required argument 'channel'"
                )
            cmd.extend(["messages", "get", "--channel", channel, "--limit", str(limit)])

        elif tool_name == "buzz_channels_list":
            cmd.extend(["channels", "list"])

        else:
            return self._build_error_envelope(
                call_id=call_id,
                tool_name=tool_name,
                category="user_error",
                code=1,
                detail=f"Unsupported buzz tool '{tool_name}'"
            )

        # Run subprocess asynchronously
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout_data, stderr_data = await proc.communicate()
            exit_code = proc.returncode

            stdout_str = stdout_data.decode("utf-8").strip()
            stderr_str = stderr_data.decode("utf-8").strip()

            if exit_code == 0:
                try:
                    parsed_result = json.loads(stdout_str) if stdout_str else {}
                except json.JSONDecodeError:
                    parsed_result = {"raw_output": stdout_str}

                return UATPEnvelope(
                    type=UATPMessageType.TOOL_RETURN,
                    source=self.endpoint,
                    destination=tool_envelope.source,
                    payload=ToolReturnPayload(
                        call_id=call_id,
                        name=tool_name,
                        status="success",
                        exit_code=0,
                        result=parsed_result
                    ).model_dump()
                )
            else:
                return self._build_error_envelope(
                    call_id=call_id,
                    tool_name=tool_name,
                    category="buzz_exec_error",
                    code=exit_code,
                    detail=stderr_str or stdout_str
                )

        except Exception as e:
            return self._build_error_envelope(
                call_id=call_id,
                tool_name=tool_name,
                category="system_error",
                code=500,
                detail=str(e)
            )

    async def get_messages(
        self,
        channel: str,
        limit: int = 20,
        since: Optional[int] = None,
        before: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve messages from a Buzz channel directly."""
        cmd = [self.buzz_binary, "--format", "compact"]
        if self.relay_url:
            cmd.extend(["--relay", self.relay_url])
        cmd.extend(["messages", "get", "--channel", channel, "--limit", str(limit)])
        if since is not None:
            cmd.extend(["--since", str(since)])
        if before is not None:
            cmd.extend(["--before", str(before)])

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout_data, _ = await proc.communicate()
        if proc.returncode != 0:
            return []

        stdout_str = stdout_data.decode("utf-8").strip()
        if not stdout_str:
            return []

        try:
            parsed = json.loads(stdout_str)
            if isinstance(parsed, list):
                return parsed
            elif isinstance(parsed, dict) and "messages" in parsed:
                return parsed["messages"]
            return [parsed]
        except json.JSONDecodeError:
            return []

    async def poll_messages(
        self,
        channel: str,
        since_timestamp: Optional[int] = None,
        poll_interval_seconds: float = 2.0,
        max_interval_seconds: float = 30.0,
        backoff_multiplier: float = 1.5,
        stop_event: Optional[asyncio.Event] = None
    ):
        """Soft-wake polling generator yielding new messages with token-saving backoff.
        
        Yields (message, timestamp).
        Automatically backs off polling intervals up to `max_interval_seconds`
        during periods of silence, and resets to `poll_interval_seconds` when active.
        """
        current_interval = poll_interval_seconds
        last_seen_ts = since_timestamp or 0

        while stop_event is None or not stop_event.is_set():
            messages = await self.get_messages(
                channel=channel,
                since=last_seen_ts if last_seen_ts > 0 else None,
                limit=50
            )

            new_messages = []
            max_ts_in_batch = last_seen_ts

            for msg in messages:
                # Handle both compact and normalized formats
                created_at = msg.get("created_at") or msg.get("time") or msg.get("timestamp") or 0
                if created_at > last_seen_ts:
                    new_messages.append(msg)
                    if created_at > max_ts_in_batch:
                        max_ts_in_batch = created_at

            if new_messages:
                last_seen_ts = max_ts_in_batch
                current_interval = poll_interval_seconds  # Reset backoff on activity
                for msg in sorted(new_messages, key=lambda m: m.get("created_at", 0)):
                    yield msg
            else:
                # Idle period: softly back off to prevent busy polling / token waste
                current_interval = min(current_interval * backoff_multiplier, max_interval_seconds)

            try:
                if stop_event:
                    await asyncio.wait_for(stop_event.wait(), timeout=current_interval)
                    break
                else:
                    await asyncio.sleep(current_interval)
            except asyncio.TimeoutError:
                pass

    def _build_error_envelope(
        self,
        call_id: str,
        tool_name: str,
        category: str,
        code: int,
        detail: str
    ) -> UATPEnvelope:
        return UATPEnvelope(
            type=UATPMessageType.ERROR,
            source=self.endpoint,
            payload=ErrorPayload(
                category=category,
                code=code,
                detail=detail,
                original_context_id=call_id
            ).model_dump()
        )
