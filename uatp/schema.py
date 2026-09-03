"""Universal Agent Translator Protocol (UATP) Schema & Data Models.

Defines Pydantic models for universal envelope validation, serialization,
and deserialization across agent harnesses and native LLM APIs.
"""

from __future__ import annotations
import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator


class UATPMessageType(str, Enum):
    HANDSHAKE = "handshake"
    CAPABILITIES = "capabilities"
    MESSAGE = "message"
    TOOL_CALL = "tool_call"
    TOOL_RETURN = "tool_return"
    STATE_PATCH = "state_patch"
    ERROR = "error"


class EndpointIdentity(BaseModel):
    agent_id: str
    runtime: str
    pubkey: Optional[str] = None
    channel_or_room: Optional[str] = None


class HandshakePayload(BaseModel):
    protocol_version: str = "1.0"
    session_id: str = Field(default_factory=lambda: f"sess_{uuid.uuid4().hex[:16]}")
    agent_identity: Dict[str, Any]
    features_supported: List[str] = Field(default_factory=list)


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class CapabilitiesPayload(BaseModel):
    context_window: Dict[str, Any] = Field(default_factory=dict)
    tools: List[ToolDefinition] = Field(default_factory=list)
    transport_modes: List[str] = Field(default_factory=list)


class MessagePayload(BaseModel):
    role: str = Field(..., description="Role: user, assistant, system, agent")
    compact_text: str
    meta: Dict[str, Any] = Field(default_factory=dict)


class ToolCallPayload(BaseModel):
    call_id: str
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class ToolReturnPayload(BaseModel):
    call_id: str
    name: str
    status: str = "success"
    exit_code: int = 0
    metrics: Dict[str, Any] = Field(default_factory=dict)
    result: Any = None


class StatePatchPayload(BaseModel):
    patch_format: str = "json_patch"
    base_state_hash: Optional[str] = None
    target_state_hash: Optional[str] = None
    patches: List[Dict[str, Any]] = Field(default_factory=list)


class ErrorPayload(BaseModel):
    category: str
    code: int = 500
    retryable: bool = False
    backoff_ms: int = 0
    detail: str
    original_context_id: Optional[str] = None


PayloadType = Union[
    HandshakePayload,
    CapabilitiesPayload,
    MessagePayload,
    ToolCallPayload,
    ToolReturnPayload,
    StatePatchPayload,
    ErrorPayload,
    Dict[str, Any]
]


class UATPEnvelope(BaseModel):
    uatp_version: str = "1.0"
    id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex}")
    trace_id: Optional[str] = Field(default_factory=lambda: f"trc_{uuid.uuid4().hex[:16]}")
    timestamp_ns: int = Field(default_factory=lambda: time.time_ns())
    type: UATPMessageType
    source: EndpointIdentity
    destination: Optional[EndpointIdentity] = None
    payload: Dict[str, Any]

    @field_validator("id")
    @classmethod
    def validate_id_prefix(cls, v: str) -> str:
        if not v.startswith("evt_"):
            raise ValueError("Envelope id must start with 'evt_'")
        return v

    def to_json(self) -> str:
        """Serialize envelope to compact, token-dense JSON string."""
        return self.model_dump_json(exclude_none=True)

    @classmethod
    def from_json(cls, json_str: str) -> UATPEnvelope:
        """Deserialize envelope from JSON string."""
        return cls.model_validate_json(json_str)
