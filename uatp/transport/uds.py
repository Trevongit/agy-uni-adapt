"""Unix Domain Socket (UDS) Transport for UATP.

Provides low-latency IPC socket server and client with binary 4-byte length-prefix framing.
"""

from __future__ import annotations
import asyncio
import os
import struct
from typing import AsyncIterator, Callable, Optional
from uatp.schema import UATPEnvelope


class UDSStreamServer:
    """Unix domain socket server handling length-prefixed UATP stream frames."""

    def __init__(self, socket_path: str = "/tmp/uatp-bus.sock", on_envelope: Optional[Callable[[UATPEnvelope], None]] = None):
        self.socket_path = socket_path
        self.on_envelope = on_envelope
        self._server: Optional[asyncio.Server] = None

    async def start(self) -> None:
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)

        self._server = await asyncio.start_unix_server(
            self._handle_client,
            path=self.socket_path
        )

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            while True:
                length_bytes = await reader.readexactly(4)
                length = struct.unpack("!I", length_bytes)[0]
                payload_bytes = await reader.readexactly(length)
                json_str = payload_bytes.decode("utf-8")
                envelope = UATPEnvelope.from_json(json_str)

                if self.on_envelope:
                    if asyncio.iscoroutinefunction(self.on_envelope):
                        response_envelope = await self.on_envelope(envelope)
                    else:
                        response_envelope = self.on_envelope(envelope)
                    if response_envelope:
                        resp_json = response_envelope.to_json().encode("utf-8")
                        writer.write(struct.pack("!I", len(resp_json)) + resp_json)
                        await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionResetError):
            pass
        finally:
            writer.close()
            await writer.wait_closed()


class UDSStreamClient:
    """Unix domain socket client for sending/receiving UATP envelopes."""

    def __init__(self, socket_path: str = "/tmp/uatp-bus.sock"):
        self.socket_path = socket_path
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None

    async def connect(self) -> None:
        self.reader, self.writer = await asyncio.open_unix_connection(self.socket_path)

    async def send(self, envelope: UATPEnvelope) -> None:
        if not self.writer:
            raise RuntimeError("Client is not connected")
        data = envelope.to_json().encode("utf-8")
        frame = struct.pack("!I", len(data)) + data
        self.writer.write(frame)
        await self.writer.drain()

    async def receive(self) -> UATPEnvelope:
        if not self.reader:
            raise RuntimeError("Client is not connected")
        length_bytes = await self.reader.readexactly(4)
        length = struct.unpack("!I", length_bytes)[0]
        payload_bytes = await self.reader.readexactly(length)
        return UATPEnvelope.from_json(payload_bytes.decode("utf-8"))

    async def close(self) -> None:
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
