# Universal Agent Translator Protocol (UATP)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Status: Alpha](https://img.shields.io/badge/Status-Alpha-orange.svg)]()

The **Universal Agent Translator Protocol (UATP)** is an open-source, ultra-low-overhead ("token-metabolic") translation protocol and routing bridge.

UATP links internal workspace agent runtimes (specifically local `block/buzz` instances pinned to `v0.5.20`, Nostr NIP-33 / NIP-34 / NIP-AP) with native LLM function-calling endpoints—such as Gemini 3.8 Flash—and external multi-host build loops (such as Grok Build's `use-buzz` skill layer).

---

## Key Principles

- **Token-Metabolic Efficiency:** Strict payload compression, byte-deterministic system instructions to maximize Gemini context caching, and delta encoding for state synchronizations.
- **Modular Decoupling:** Universal envelope schemas decouple internal agent execution environments from upstream LLM APIs and IPC buses.
- **Unified IPC & Transport:** Native support for length-prefixed Unix Domain Sockets (`/tmp/uatp-bus.sock`) and atomic file-bus mailboxes.

---

## Repository Structure

```text
├── TRANSLATOR_SPEC.md     # Foundational architecture specification & boundary definition
├── schemas/
│   └── uatp_v1.json       # JSON Schema definition for UATP v1 envelope & payloads
├── uatp/
│   ├── __init__.py        # Python package core
│   ├── adapters/          # Model adapters (Gemini 3.8/3.7 native function calling)
│   ├── connectors/        # Workspace connectors (Buzz CLI & Unix sockets)
│   └── transport/         # Low-latency IPC stream framing & file-bus
├── tests/                 # Unit test suite & validation matrix
├── pyproject.toml         # Build specification & dependencies
└── LICENSE                # MIT License
```

---

## Quickstart

### 1. Inspect the Specification
Read [TRANSLATOR_SPEC.md](TRANSLATOR_SPEC.md) for full protocol schemas, type definitions, and mapping tables.

### 2. Validate Schema
```bash
python3 -m unittest discover tests
```

---

## License
MIT License.
