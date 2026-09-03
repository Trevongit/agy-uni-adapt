"""Universal Agent Translator Protocol (UATP) Core Module."""

from uatp.schema import (
    UATPEnvelope,
    UATPMessageType,
    EndpointIdentity,
    HandshakePayload,
    ToolDefinition,
    CapabilitiesPayload,
    MessagePayload,
    ToolCallPayload,
    ToolReturnPayload,
    StatePatchPayload,
    ErrorPayload,
)
from uatp.adapters.gemini import GeminiNativeAdapter
from uatp.connectors.buzz import BuzzLocalConnector
from uatp.transport.uds import UDSStreamServer, UDSStreamClient

__version__ = "1.0.0-alpha"

__all__ = [
    "__version__",
    "UATPEnvelope",
    "UATPMessageType",
    "EndpointIdentity",
    "HandshakePayload",
    "ToolDefinition",
    "CapabilitiesPayload",
    "MessagePayload",
    "ToolCallPayload",
    "ToolReturnPayload",
    "StatePatchPayload",
    "ErrorPayload",
    "GeminiNativeAdapter",
    "BuzzLocalConnector",
    "UDSStreamServer",
    "UDSStreamClient",
]
