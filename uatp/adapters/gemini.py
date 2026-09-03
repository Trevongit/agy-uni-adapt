"""Gemini 3.8 / 3.7 Native Adapter for UATP.

Provides bidirectional transformation between Google Gemini native API
structures (contents, function calls, function declarations) and UATP envelopes
while optimizing for Gemini 3.8 token metabolism and context caching.
"""

from __future__ import annotations
import hashlib
from typing import Any, Dict, List, Optional, Tuple
from uatp.schema import (
    UATPEnvelope,
    UATPMessageType,
    EndpointIdentity,
    ToolCallPayload,
    ToolReturnPayload,
    MessagePayload,
    CapabilitiesPayload
)


class GeminiNativeAdapter:
    """Adapts native Gemini 3.8 API shapes to and from UATP envelopes."""

    def __init__(self, agent_id: str = "gemini-3.8-adapter", default_model: str = "gemini-3.8-flash"):
        self.agent_id = agent_id
        self.default_model = default_model
        self.source_identity = EndpointIdentity(agent_id=self.agent_id, runtime="gemini-native-adapter")

    @staticmethod
    def compute_cache_fingerprint(system_prompt: str, tools: List[Dict[str, Any]]) -> str:
        """Compute stable SHA-256 hash for prefix context caching."""
        hasher = hashlib.sha256()
        hasher.update(system_prompt.strip().encode("utf-8"))
        for tool in sorted(tools, key=lambda t: t.get("name", "")):
            hasher.update(str(tool).encode("utf-8"))
        return hasher.hexdigest()

    def uatp_to_gemini_content(self, envelope: UATPEnvelope) -> Dict[str, Any]:
        """Convert a UATP envelope into a native Gemini Content dictionary."""
        msg_type = envelope.type
        payload = envelope.payload

        if msg_type == UATPMessageType.MESSAGE:
            role = payload.get("role", "user")
            # Gemini expects 'user' or 'model' (or system instruction separately)
            gemini_role = "model" if role in ("assistant", "agent", "model") else "user"
            return {
                "role": gemini_role,
                "parts": [{"text": payload.get("compact_text", "")}]
            }

        elif msg_type == UATPMessageType.TOOL_CALL:
            return {
                "role": "model",
                "parts": [{
                    "functionCall": {
                        "name": payload.get("name", ""),
                        "args": payload.get("arguments", {})
                    }
                }]
            }

        elif msg_type == UATPMessageType.TOOL_RETURN:
            # Gemini returns function responses under role 'function' or 'user' with functionResponse part
            return {
                "role": "function",
                "parts": [{
                    "functionResponse": {
                        "name": payload.get("name", ""),
                        "response": {
                            "result": payload.get("result"),
                            "status": payload.get("status", "success"),
                            "exit_code": payload.get("exit_code", 0)
                        }
                    }
                }]
            }

        raise ValueError(f"Envelope type {msg_type} cannot be directly converted to Gemini Content turn")

    def gemini_response_to_uatp(self, response_dict: Dict[str, Any], destination: Optional[EndpointIdentity] = None) -> List[UATPEnvelope]:
        """Convert raw Gemini generateContent response into standard UATP envelopes.
        
        Handles text candidate parts and function call requests.
        """
        envelopes: List[UATPEnvelope] = []
        candidates = response_dict.get("candidates", [])
        if not candidates:
            return envelopes

        first_candidate = candidates[0]
        content = first_candidate.get("content", {})
        parts = content.get("parts", [])

        for idx, part in enumerate(parts):
            if "functionCall" in part:
                fc = part["functionCall"]
                call_id = fc.get("id") or f"call_{fc.get('name', 'fn')}_{idx}"
                envelope = UATPEnvelope(
                    type=UATPMessageType.TOOL_CALL,
                    source=self.source_identity,
                    destination=destination,
                    payload=ToolCallPayload(
                        call_id=call_id,
                        name=fc.get("name", ""),
                        arguments=fc.get("args", {})
                    ).model_dump()
                )
                envelopes.append(envelope)

            elif "text" in part:
                envelope = UATPEnvelope(
                    type=UATPMessageType.MESSAGE,
                    source=self.source_identity,
                    destination=destination,
                    payload=MessagePayload(
                        role="assistant",
                        compact_text=part["text"],
                        meta={"finish_reason": first_candidate.get("finishReason", "STOP")}
                    ).model_dump()
                )
                envelopes.append(envelope)

        return envelopes

    def tools_to_gemini_declarations(self, capabilities: CapabilitiesPayload) -> List[Dict[str, Any]]:
        """Convert UATP tool capabilities into Gemini FunctionDeclaration format."""
        declarations = []
        for tool in capabilities.tools:
            declarations.append({
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            })
        return declarations
