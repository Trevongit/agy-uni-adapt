"""Comprehensive Validation Suite for UATP Core, Gemini Adapter, and Transport."""

import asyncio
import json
import os
import unittest
from pathlib import Path
import jsonschema

from uatp.schema import (
    UATPEnvelope,
    UATPMessageType,
    EndpointIdentity,
    ToolCallPayload,
    ToolReturnPayload,
    MessagePayload,
    CapabilitiesPayload,
    ToolDefinition
)
from uatp.adapters.gemini import GeminiNativeAdapter
from uatp.connectors.buzz import BuzzLocalConnector
from uatp.transport.uds import UDSStreamServer, UDSStreamClient


class TestUATPSchema(unittest.TestCase):
    def setUp(self):
        schema_path = Path(__file__).parent.parent / "schemas" / "uatp_v1.json"
        with open(schema_path, "r") as f:
            self.schema = json.load(f)

    def test_schema_compliance_tool_call(self):
        envelope = UATPEnvelope(
            type=UATPMessageType.TOOL_CALL,
            source=EndpointIdentity(agent_id="test-agent", runtime="antigravity"),
            destination=EndpointIdentity(agent_id="buzz-seat", runtime="buzz-connector"),
            payload=ToolCallPayload(
                call_id="call_01",
                name="buzz_messages_send",
                arguments={"channel": "chan_123", "content": "Hello Buzz"}
            ).model_dump()
        )
        raw_dict = json.loads(envelope.to_json())
        jsonschema.validate(instance=raw_dict, schema=self.schema)

    def test_schema_compliance_message(self):
        envelope = UATPEnvelope(
            type=UATPMessageType.MESSAGE,
            source=EndpointIdentity(agent_id="gemini", runtime="native"),
            payload=MessagePayload(
                role="assistant",
                compact_text="Status OK"
            ).model_dump()
        )
        raw_dict = json.loads(envelope.to_json())
        jsonschema.validate(instance=raw_dict, schema=self.schema)


class TestGeminiAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = GeminiNativeAdapter()

    def test_roundtrip_gemini_tool_call(self):
        # Simulate Gemini raw response
        gemini_resp = {
            "candidates": [{
                "content": {
                    "role": "model",
                    "parts": [{
                        "functionCall": {
                            "name": "buzz_messages_send",
                            "args": {"channel": "uuid-1", "content": "test payload"}
                        }
                    }]
                },
                "finishReason": "STOP"
            }]
        }

        envelopes = self.adapter.gemini_response_to_uatp(gemini_resp)
        self.assertEqual(len(envelopes), 1)
        env = envelopes[0]
        self.assertEqual(env.type, UATPMessageType.TOOL_CALL)
        self.assertEqual(env.payload["name"], "buzz_messages_send")
        self.assertEqual(env.payload["arguments"]["channel"], "uuid-1")

        # Now convert to Gemini Content turn
        gemini_content = self.adapter.uatp_to_gemini_content(env)
        self.assertEqual(gemini_content["role"], "model")
        self.assertEqual(gemini_content["parts"][0]["functionCall"]["name"], "buzz_messages_send")

    def test_prefix_cache_fingerprint(self):
        system_prompt = "You are a concise workspace agent."
        tools = [{"name": "buzz_send", "description": "send"}]
        hash1 = self.adapter.compute_cache_fingerprint(system_prompt, tools)
        hash2 = self.adapter.compute_cache_fingerprint(system_prompt, tools)
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 64)


class TestUDSTransport(unittest.IsolatedAsyncioTestCase):
    async def test_socket_ipc_roundtrip(self):
        sock_path = "/tmp/uatp-test.sock"

        def echo_handler(env: UATPEnvelope):
            return UATPEnvelope(
                type=UATPMessageType.TOOL_RETURN,
                source=EndpointIdentity(agent_id="server", runtime="uds"),
                destination=env.source,
                payload=ToolReturnPayload(
                    call_id="echo_1",
                    name="echo",
                    status="success",
                    result={"ack": True}
                ).model_dump()
            )

        server = UDSStreamServer(socket_path=sock_path, on_envelope=echo_handler)
        await server.start()

        try:
            client = UDSStreamClient(socket_path=sock_path)
            await client.connect()

            request = UATPEnvelope(
                type=UATPMessageType.MESSAGE,
                source=EndpointIdentity(agent_id="client", runtime="uds"),
                payload=MessagePayload(role="user", compact_text="ping").model_dump()
            )
            await client.send(request)
            response = await client.receive()

            self.assertEqual(response.type, UATPMessageType.TOOL_RETURN)
            self.assertEqual(response.payload["status"], "success")
            await client.close()
        finally:
            await server.stop()


class TestBuzzConnector(unittest.TestCase):
    def test_binary_discovery(self):
        connector = BuzzLocalConnector()
        # Binary should be discovered at ~/.local/bin/buzz
        self.assertTrue(connector.is_available())


class TestSoftWakePolling(unittest.IsolatedAsyncioTestCase):
    async def test_poll_messages_debounced_stop(self):
        connector = BuzzLocalConnector()
        stop_event = asyncio.Event()

        # Mock get_messages to return sample messages
        async def mock_get_messages(channel: str, limit: int = 20, since=None, before=None):
            if since and since >= 100:
                return []
            return [{"id": "m1", "created_at": 100, "content": "hi"}]

        connector.get_messages = mock_get_messages  # type: ignore

        collected = []
        async def run_poll():
            async for msg in connector.poll_messages(
                channel="mock-channel",
                since_timestamp=0,
                poll_interval_seconds=0.01,
                max_interval_seconds=0.05,
                stop_event=stop_event
            ):
                collected.append(msg)
                if len(collected) >= 1:
                    stop_event.set()

        await asyncio.wait_for(run_poll(), timeout=2.0)
        self.assertEqual(len(collected), 1)
        self.assertEqual(collected[0]["id"], "m1")

    async def test_async_uds_handler(self):
        sock_path = "/tmp/uatp-async-test.sock"

        async def async_handler(env: UATPEnvelope):
            await asyncio.sleep(0.01)
            return UATPEnvelope(
                type=UATPMessageType.HANDSHAKE,
                source=EndpointIdentity(agent_id="bridge", runtime="uds"),
                destination=env.source,
                payload={"status": "ready"}
            )

        server = UDSStreamServer(socket_path=sock_path, on_envelope=async_handler)
        await server.start()

        try:
            client = UDSStreamClient(socket_path=sock_path)
            await client.connect()

            req = UATPEnvelope(
                type=UATPMessageType.HANDSHAKE,
                source=EndpointIdentity(agent_id="client", runtime="test"),
                payload={"protocol_version": "1.0"}
            )
            await client.send(req)
            resp = await client.receive()
            self.assertEqual(resp.type, UATPMessageType.HANDSHAKE)
            self.assertEqual(resp.payload["status"], "ready")
            await client.close()
        finally:
            await server.stop()


if __name__ == "__main__":
    unittest.main()
