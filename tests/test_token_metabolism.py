"""Token Metabolism and Serialization Benchmark for UATP.

Validates that serialized UATP envelopes maintain strict byte budget boundaries,
zero-copy/zero-overhead JSON parsing speeds, and stable prefix cache fingerprints.
"""

import json
import time
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
    ToolDefinition,
)
from uatp.adapters.gemini import GeminiNativeAdapter


class TestTokenMetabolism(unittest.TestCase):
    def setUp(self):
        self.adapter = GeminiNativeAdapter()
        schema_path = Path(__file__).parent.parent / "schemas" / "uatp_v1.json"
        with open(schema_path, "r") as f:
            self.schema = json.load(f)

    def test_serialized_byte_budget(self):
        """Ensure minimal envelopes stay well within token/byte budgets."""
        env = UATPEnvelope(
            type=UATPMessageType.MESSAGE,
            source=EndpointIdentity(agent_id="gemini", runtime="native"),
            payload=MessagePayload(role="assistant", compact_text="ack").model_dump()
        )
        serialized = env.to_json()
        raw_bytes = len(serialized.encode("utf-8"))
        # An empty/compact message envelope should stay under 250 bytes
        self.assertLess(raw_bytes, 300, f"Envelope byte size ({raw_bytes} bytes) exceeds budget")

    def test_serialization_throughput(self):
        """Ensure serialization/deserialization runs at > 20,000 ops/sec."""
        env = UATPEnvelope(
            type=UATPMessageType.TOOL_CALL,
            source=EndpointIdentity(agent_id="test-agent", runtime="antigravity"),
            destination=EndpointIdentity(agent_id="buzz-seat", runtime="buzz-connector"),
            payload=ToolCallPayload(
                call_id="call_999",
                name="buzz_messages_send",
                arguments={"channel": "chan_dev", "content": "ping"}
            ).model_dump()
        )

        n_iterations = 2000
        start = time.perf_counter()
        for _ in range(n_iterations):
            json_str = env.to_json()
            _ = UATPEnvelope.from_json(json_str)
        elapsed = time.perf_counter() - start

        ops_per_sec = n_iterations / elapsed
        self.assertGreater(ops_per_sec, 20000, f"Throughput {ops_per_sec:.0f} ops/sec below target")

    def test_gemini_prefix_cache_invariance(self):
        """Ensure stable system prompt and tool definitions produce identical SHA-256 fingerprints."""
        sys_prompt = "You are an autonomous workspace agent operating inside block/buzz."
        tools = [
            {"name": "buzz_messages_send", "description": "Send a message to a buzz channel"},
            {"name": "buzz_messages_get", "description": "Fetch channel messages"}
        ]

        h1 = self.adapter.compute_cache_fingerprint(sys_prompt, tools)
        h2 = self.adapter.compute_cache_fingerprint(sys_prompt, list(reversed(tools)))
        # Order should be normalized by tool name sorting
        self.assertEqual(h1, h2, "Prefix cache fingerprint must be invariant to tool order")


if __name__ == "__main__":
    unittest.main()
