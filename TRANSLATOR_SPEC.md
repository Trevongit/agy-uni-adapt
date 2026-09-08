# UNIVERSAL AGENT TRANSLATOR PROTOCOL (UATP)
## Architectural Specification & Boundary Definition (`v1.0.0-alpha`)

### Target Context
* **Host Platform:** Linux Mint / POSIX
* **Reference Substrate:** Local `buzz-cli` against a live Buzz community (`Nostr NIP-33 / NIP-34 / NIP-AP` agent harness & transport)
* **Native Model Targets:** Google Gemini 3.8 / 3.7 Flash (`gemini-3.8-flash`, native function-calling & context caching)
* **External Companion Co-Lab:** Grok Build `use-buzz` skill runtime / Multi-host collaborative bus
* **Upstream Target:** Public open-source repository under `@Trevongit`

---

## 1. Core Architectural Tenets

### 1.1 Token-Metabolic Efficiency (Lean I/O)
1. **Context-Cache Maximization:** Gemini 3.8 supports implicit and explicit context caching. System prompts, static capability manifests, and schema definitions must remain byte-deterministic across turns to hit the token cache prefix.
2. **Dense Ephemeral Payloads:** Avoid prose explanations in internal agent-to-agent or agent-to-harness packets. Payloads use concise keyed structures (e.g., short key mapping or compact JSON array forms) eliminating redundant round-trip tokens.
3. **Delta Encoding for State Synchronizations:** Rather than broadcasting full context frames across the bus, agents emit unified diffs or JSON Patch (RFC 6902) mutations against an agreed state vector.

### 1.2 Modular Decoupling
1. **Engine Independence:** The protocol layer is decoupled from specific client libraries. It operates as a bi-directional translation pipeline:
   ```
   [Buzz Workspace / Nostr Bus] <---> [UATP Router / Normalizer] <---> [Provider Adapters] <---> [Gemini / Grok / Claude]
   ```
2. **Abstract Capability Negotiation:** Agent runtimes do not assume uniform feature support. On handshake, agents negotiate tool interfaces, context ceilings, and compression schemas via `Capabilities_Exchange`.

### 1.3 State Continuity & Bus Transport
1. **IPC Layer:** Low-latency Unix Domain Sockets (`UDS`) for daemonized local agents (`/tmp/uatp-<seat>.sock`) with fallback to atomic file-bus mailboxes (`~/.buzz/OUTBOX`, `~/.buzz/.scratch`).
2. **Deterministic Correlation IDs:** Ephemeral messages track parent event IDs and causal vector clocks (`turn_id`, `trace_id`, `span_id`) across asynchronous process handoffs.

---

## 2. UATP Schema Specification (`UATP_SCHEMA v1`)

All UATP packet envelopes conform to the base specification:

```json
{
  "uatp_version": "1.0",
  "id": "evt_01J6ABCDEF1234567890",
  "trace_id": "trc_9876543210ABCDEF",
  "timestamp_ns": 1725338400000000000,
  "type": "handshake | capabilities | message | tool_call | tool_return | state_patch | error",
  "source": {
    "agent_id": "seat-ag-gemini38",
    "runtime": "antigravity-cli",
    "pubkey": "npub1..."
  },
  "destination": {
    "agent_id": "buzz-grok-build",
    "runtime": "grok-build",
    "channel_or_room": "room-uuid-or-id"
  },
  "payload": {}
}
```

### 2.1 Identity & Session Handshake (`type: "handshake"`)
Initiates communication between local workspace processes and the translation router.
```json
{
  "type": "handshake",
  "payload": {
    "protocol_version": "1.0",
    "session_id": "sess_01J6ABC0011223344",
    "agent_identity": {
      "display_name": "Antigravity-3.8-Flash",
      "harness": "antigravity",
      "model_descriptor": "gemini-3.8-flash",
      "pubkey": "4c0f87898516e8b79f6e5229be49b92dd0a5ee3628e930bfdc46497f625e1a12"
    },
    "features_supported": ["context_caching", "streaming_tools", "binary_delta", "nip34_git"]
  }
}
```

### 2.2 Capabilities Exchange (`type: "capabilities"`)
Exchanges runtime operational ceilings and available function tooling.
```json
{
  "type": "capabilities",
  "payload": {
    "context_window": {
      "max_tokens": 1048576,
      "cache_ttl_seconds": 3600,
      "recommended_chunk_tokens": 4096
    },
    "tools": [
      {
        "name": "buzz_messages_send",
        "description": "Send a verified message to a Buzz channel or thread.",
        "parameters": {
          "type": "object",
          "properties": {
            "channel": { "type": "string", "description": "Target Channel UUID" },
            "content": { "type": "string", "description": "Markdown body content" },
            "mentions": { "type": "array", "items": { "type": "string" } }
          },
          "required": ["channel", "content"]
        }
      }
    ],
    "transport_modes": ["unix_socket", "file_bus", "memory_mapped"]
  }
}
```

### 2.3 Tool Call & Execution Feedback (`type: "tool_call" | "tool_return"`)
Bi-directional invocation mapped transparently between Gemini tool calling declarations and Buzz CLI / host actions.

**Tool Call Request:**
```json
{
  "type": "tool_call",
  "payload": {
    "call_id": "call_gemini_38_0192",
    "name": "buzz_messages_send",
    "arguments": {
      "channel": "a53dc37c-1604-4fbc-a75b-fc236057a5d5",
      "content": "Status sync: UATP protocol boundary operational."
    }
  }
}
```

**Execution Feedback Return:**
```json
{
  "type": "tool_return",
  "payload": {
    "call_id": "call_gemini_38_0192",
    "name": "buzz_messages_send",
    "status": "success",
    "exit_code": 0,
    "metrics": {
      "duration_ms": 42,
      "bytes_written": 74
    },
    "result": {
      "event_id": "ee489df1a07bbfae...",
      "accepted": true,
      "message": "Message confirmed on relay"
    }
  }
}
```

### 2.4 Message Payload (`type: "message"`)
Lean formatting for textual, system, and context messages, stripping token-heavy wrappers:
```json
{
  "type": "message",
  "payload": {
    "role": "user | assistant | system | agent",
    "compact_text": "Clean unadorned message content",
    "meta": {
      "channel_id": "uuid",
      "parent_event_id": "hex",
      "is_context_boundary": false
    }
  }
}
```

### 2.5 State Error Handling (`type: "error"`)
Unified error categorization mapping POSIX errors, Buzz CLI exit codes, and Gemini API errors:
```json
{
  "type": "error",
  "payload": {
    "category": "user_error | network_timeout | auth_failure | schema_mismatch | provider_rate_limit",
    "code": 429,
    "retryable": true,
    "backoff_ms": 1500,
    "detail": "Gemini resource exhausted: quota exceeded for model gemini-3.8-flash",
    "original_context_id": "call_gemini_38_0192"
  }
}
```

---

## 3. Gemini 3.8 Native Adapter Harness

The Gemini Native Adapter converts between standard Google GenAI / Vertex AI JSON interfaces and internal UATP events.

### 3.1 Schema Mapping Table

| Gemini Native Entity | UATP Envelope Equivalent | Optimization Pass |
|---|---|---|
| `Content(role='user', parts=[TextPart])` | `UATP[type="message", payload.role="user"]` | Strips outer list nesting, flattens text. |
| `Content(role='model', parts=[FunctionCall])` | `UATP[type="tool_call"]` | Extracts `name` and `args` directly into call vector. |
| `Content(role='function', parts=[FunctionResponse])` | `UATP[type="tool_return"]` | Converts tool execution result into canonical JSON payload. |
| `SystemInstruction` | `UATP[type="handshake"].payload.system_prompt` | Cached via stable hash prefix; excluded from regular turn rounds. |
| `FinishReason` | `UATP[payload.meta.finish_reason]` | Normalized into `stop`, `tool_calls`, `length`, `content_filter`. |

### 3.2 Token-Metabolic Context Ingestion Pipeline
1. **Cache Pinned Header:** Prepares static system instructions and tool definitions once:
   ```json
   {
     "cachedContent": {
       "model": "models/gemini-3.8-flash",
       "ttl": "3600s",
       "contents": [ ...static_system_and_tools... ]
     }
   }
   ```
2. **Turn-Level Message Trimming:** History passing over the wire uses minimal key tokens (`r` for role, `c` for content, `t` for tool_calls) inside internal memory before hydrating into Gemini API shapes.

---

## 4. Local Buzz Connector Interface (`v0.5.20` Integration)

The Buzz connector maps workspace events directly to/from Buzz's local filesystem and CLI layers:

```
                  +-----------------------------------+
                  |           Buzz Workspace          |
                  |  (~/.buzz / Nostr Relay / Events) |
                  +-----------------+-----------------+
                                    |
            [NIP-33 / NIP-34 / NIP-AP Events & CLI Output]
                                    |
                                    v
                  +-----------------+-----------------+
                  |      Buzz Local Connector         |
                  |   (Python/Rust async pipe bridge) |
                  +-----------------+-----------------+
                                    |
                      [Normalized UATP Envelopes]
                                    |
                                    v
                  +-----------------+-----------------+
                  |      UATP Routing Core            |
                  |   (Unix Domain Socket / IPC Bus)  |
                  +--------+-----------------+--------+
                           |                 |
      [Gemini Native Adapter]               [External Grok Build /
      (API / Function Calls)                 Modified Skill Socket]
```

### 4.1 Transport Substrates
1. **Unix Domain Socket Server (`UATPServer`):** Run on host as `/tmp/uatp-bus.sock`. Subscribes to events with stream framing: `[uint32_length_be][utf8_json_payload]`.
2. **CLI Exec Adapter:** Interacts with `/home/trev/.local/bin/buzz` using `--format compact` to minimize process stdout token consumption.

---

## 5. Verification & Testing Matrix

| Metric | Target Boundary | Validation Method |
|---|---|---|
| **Serialization Overhead** | < 1.0 ms for 10KB payload | Benchmarked across Python `msgspec` / `ujson` and Rust `serde_json` |
| **Token Conservation Ratio** | ≥ 45% reduction vs naive chat completions | Tokenizer token count comparison against raw conversation transcripts |
| **Schema Compliance** | 100% pass on JSON Schema test suites | Python `jsonschema` and pytest suites |
| **Crash & Reconnection Resilience** | Auto-recover socket within 250ms | Signal injection (SIGPIPE, process restarts) |

---
*Specification approved for baseline implementation.*
