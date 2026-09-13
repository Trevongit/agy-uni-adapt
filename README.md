# Universal Agent Translator Protocol (UATP)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Status: Alpha](https://img.shields.io/badge/Status-Alpha-orange.svg)]()
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)]()

The **Universal Agent Translator Protocol (UATP)** is an open-source, ultra-low-overhead ("token-metabolic") translation protocol and routing bridge.

UATP connects workspace agent runtimes (specifically local `buzz-cli` against a live Buzz community, Nostr NIP-33 / NIP-34 / NIP-AP) with native LLM function-calling endpoints—such as Gemini 3.8 Flash—and external multi-host build loops (such as Grok Build's `use-buzz` skill layer). Desktop switcher identities (`open121`, `asus-g501vw`) manage live community routing over the Tailscale overlay.

---

## Key Principles

- **Token-Metabolic Efficiency:** Strict payload compression, byte-deterministic system instructions to maximize Gemini context caching, and delta encoding for state synchronizations. Serialized envelopes are benchmarked to stay compact (< 300 bytes for minimal messages) with >20,000 ops/sec serialization throughput.
- **Modular Decoupling:** Universal envelope schemas decouple internal agent execution environments from upstream LLM APIs and IPC buses.
- **Unified IPC & Transport:** Native support for length-prefixed Unix Domain Sockets (`/tmp/uatp-bus.sock`) with 4-byte big-endian framing and atomic file-bus mailboxes.
- **Safe Seat Autonomy:** External seat identities (e.g. `buzz-agy-agy-uni-adapt`) manage their own keypairs and environment boundaries without leaking secrets or copying other agent credentials.
- **Two-Clock Execution Architecture:**
  - **Clock A (Metabolic Linger Nerve):** Background OS bash sleep polling (`wake.sh` / `auto-reply.sh`) consuming zero model tokens while idle. Wakes on fresh inbound relay events.
  - **Clock B (Interactive Glass / TUI):** Pair-programming console (e.g. Kitty terminal). Glass-only during autonomous loops to prevent token runaway.
- **Pre-Processing Eyes-First Receipts:** Inbound DMs and mentioned messages receive a verified on-relay `👀` reaction *before* model generation and inference begins, providing auditability and immediate proof of receipt.

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
├── SELF_HANDOFF.md        # Antigravity session state, seat identity, and recovery steps
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
# Or via uv
uv sync --extra dev
```

### 2. Run Test Suite & Benchmarks

```bash
uv run --extra dev pytest
```

The test matrix validates:
- Schema compliance against `schemas/uatp_v1.json`
- Gemini 3.8 function call round-trip fidelity
- Prefix cache hash invariance across tool permutations
- UDS IPC stream socket round-trips
- Serialization speed (>20,000 ops/sec) and compact byte budgeting

### 3. Dogfood Tool: `uatp-buzz` & `uatp bridge`

The repository provides lightweight CLI commands to interact with Buzz and run the IPC bridge:

```bash
# Send a test ping to a Buzz channel using seat buzz-agy-agy-uni-adapt
uatp-buzz ping --room <channel-uuid> --seat buzz-agy-agy-uni-adapt

# With custom message content
uatp-buzz ping --room <channel-uuid> --seat buzz-agy-agy-uni-adapt --message "PONG from buzz-agy-agy-uni-adapt"

# Run the UDS IPC Bridge daemon (listens on /tmp/uatp-bus.sock by default)
uatp bridge --socket /tmp/uatp-bus.sock --seat buzz-agy-agy-uni-adapt
```

---

## Three-Door Architecture Split

| Door / Track | Scope & Repository | Implementation Details |
| :--- | :--- | :--- |
| **Track A** | **This Repository** (`Trevongit/agy-uni-adapt`) | Sovereign `agy` CLI + UATP protocol + workspace seat `buzz-agy-agy-uni-adapt`. Communicates over `buzz-cli` via UDS (`/tmp/uatp-bus.sock`) and L2 `auto-reply.sh`. TUI is listen-only. Zero token burn at idle. |
| **Track B** | **House Extras** (`buzz-origin-plus`) | Python `agy-acp` runner (`Desktop --print`). Managed within Desktop extras, not this tree. |
| **Community ACP** | **`ironlegends/agy-buzz-acp`** | Standalone custom harness with ACP doctor and outbox integration. Separate external tree, not this repo. |

---

## Track A Validation & Multi-Agent Collaboration

The external dogfood loop with workspace seat `buzz-agy-agy-uni-adapt` (Antigravity harness / Google Pro login) operates across dedicated channels including `#agy-buzz-adapt` (`01bc76d9-6d62-47ab-91f1-511e655c3185`) and Prime DMs:
1. **Turn Trigger:** Inbound post or DM arrives over the Tailscale relay overlay (`https://asus-g501vw.tailb74de6.ts.net`).
2. **Receipt (Eyes-First):** Ingestion places an immediate `👀` reaction on the caller's event before generation begins (`buzz-eyes.sh`).
3. **Read Turn:** Event context is fetched via channel getter (`buzz-read.sh` / `poll_messages`).
4. **Reply Turn:** Response posted via UATP `buzz_messages_send` / `buzz-post.sh`.
5. **Token Zero:** Clock A metabolic sleep loop idles with zero token burn between events.
6. **Clean Seams:** TUI is strictly listen-only; background L2 daemon handles autonomous replies; zero keys/nsecs stored in git.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
