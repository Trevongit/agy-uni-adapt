"""Buzz Local Connector for UATP.

Integrates with local block/buzz workspaces (pinned to v0.5.20), invoking
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
            runtime="buzz-connector-v0.5.20"
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
