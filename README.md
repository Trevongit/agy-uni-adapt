# Universal Agent Translator Protocol (UATP)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Status: Alpha](https://img.shields.io/badge/Status-Alpha-orange.svg)]()
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)]()

The **Universal Agent Translator Protocol (UATP)** is an open-source, ultra-low-overhead ("token-metabolic") translation protocol and routing bridge.

UATP connects workspace agent runtimes (specifically local `block/buzz` instances pinned to `v0.5.20`, Nostr NIP-33 / NIP-34 / NIP-AP) with native LLM function-calling endpoints—such as Gemini 3.8 Flash—and external multi-host build loops (such as Grok Build's `use-buzz` skill layer).

---

## Key Principles

- **Token-Metabolic Efficiency:** Strict payload compression, byte-deterministic system instructions to maximize Gemini context caching, and delta encoding for state synchronizations. Serialized envelopes are benchmarked to stay compact (< 300 bytes for minimal messages) with >20,000 ops/sec serialization throughput.
- **Modular Decoupling:** Universal envelope schemas decouple internal agent execution environments from upstream LLM APIs and IPC buses.
- **Unified IPC & Transport:** Native support for length-prefixed Unix Domain Sockets (`/tmp/uatp-bus.sock`) with 4-byte big-endian framing and atomic file-bus mailboxes.
- **Safe Seat Autonomy:** External seat identities (e.g. `agy-buzz`) manage their own keypairs and environment boundaries without leaking secrets or copying other agent credentials.

---

## Architecture Overview

```
                      +-----------------------------+
                      |   Google Gemini 3.8 Flash   |
                      | (Native Function-Calling API)|
                      +--------------+--------------+
                                     |
                         JSON Parts / Tool Calls
                                     |
                                     v
                      +-----------------------------+
                      |     uatp.adapters.gemini    |
                      |    (GeminiNativeAdapter)    |
                      | - Prefix Cache Pinning (SHA)|
                      | - Content/Response Mappings |
                      +--------------+--------------+
                                     |
                           UATP v1 Envelopes
                         (Structured Msg / Tools)
                                     |
            +------------------------+------------------------+
            |                                                 |
            v                                                 v
+-------------------------+                       +-------------------------+
|   uatp.transport.uds    |                       |  uatp.connectors.buzz   |
|   (UDSStreamServer /    |                       |   (BuzzLocalConnector)  |
|    UDSStreamClient)     |                       | - Invokes Buzz CLI      |
| Length-prefixed IPC Bus |                       |   (--format compact)    |
|   /tmp/uatp-bus.sock    |                       | - Routes Send / Get     |
+-------------------------+                       +------------+------------+
                                                               |
                                                               v
                                                  +-------------------------+
                                                  |    Local Buzz Substrate |
                                                  | (Nostr Relay / Channels)|
                                                  +-------------------------+
```

---

## Repository Structure

```text
├── TRANSLATOR_SPEC.md     # Foundational architecture specification & boundary definition
├── schemas/
│   └── uatp_v1.json       # JSON Schema definition for UATP v1 envelope & payloads
├── uatp/
│   ├── __init__.py        # Public package exports
│   ├── schema.py          # Pydantic v2 data models for UATP envelopes
│   ├── cli.py             # uatp-buzz CLI tool for dogfooding
│   ├── adapters/
│   │   └── gemini.py      # Gemini 3.8/3.7 native function calling adapter
│   ├── connectors/
│   │   └── buzz.py        # BuzzLocalConnector interfacing with buzz CLI
│   └── transport/
│       └── uds.py         # Length-prefixed Unix Domain Socket transport
├── tests/
│   ├── test_uatp.py       # Core schema validation, Gemini roundtrip, UDS IPC
│   └── test_token_metabolism.py # Performance benchmarks and token budgeting
├── pyproject.toml         # Build specification, dependencies & console scripts
├── HANDOFF.md             # Multi-session handoff state & roadmap tracking
└── LICENSE                # MIT License
```

---

## Quickstart

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/Trevongit/agy-uni-adapt.git
cd agy-uni-adapt

# Install dependencies
pip install -e .
```

### 2. Run Test Suite & Benchmarks

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

The test matrix validates:
- Schema compliance against `schemas/uatp_v1.json`
- Gemini 3.8 function call round-trip fidelity
- Prefix cache hash invariance across tool permutations
- UDS IPC stream socket round-trips
- Serialization speed (>20,000 ops/sec) and compact byte budgeting

### 3. Dogfood Tool: `uatp-buzz`

The repository provides a dogfood CLI command to send test pings/pongs to Buzz channels using the `BuzzLocalConnector`:

```bash
# Send a test ping to a Buzz channel using seat agy-buzz
uatp-buzz ping --room <channel-uuid> --seat agy-buzz

# With custom message content
uatp-buzz ping --room <channel-uuid> --seat agy-buzz --message "PONG from agy-buzz"
```

---

## Track A Validation (Proven in Live Collab)

The 2-way external dogfood loop between `agy-buzz` (Antigravity harness) and `Buzz-grok` (Grok Build seat) has been proven and closed in `#agy-buzz-adapt` (`01bc76d9-6d62-47ab-91f1-511e655c3185`):
1. **Turn Trigger:** Mention / PING posted by Buzz-grok.
2. **Read Turn:** `agy-buzz` reads via channel getter.
3. **Reply Turn:** `agy-buzz` sends PONG using UATP `buzz_messages_send` (`BuzzLocalConnector` tool call / `uatp-buzz ping`).
4. **Token Zero:** External seat idles between turns with zero token burn.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
